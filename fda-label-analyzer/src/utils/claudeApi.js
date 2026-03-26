import { EXTRACTION_SYSTEM_PROMPT, CONVERSION_SYSTEM_PROMPT } from './prompts.js';

const MODEL = 'claude-opus-4-5';
const API_URL = 'https://api.anthropic.com/v1/messages';

async function callClaude(apiKey, systemPrompt, userContent, maxTokens = 8192) {
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true',
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: maxTokens,
      system: systemPrompt,
      messages: [{ role: 'user', content: userContent }],
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Claude API error ${res.status}: ${body}`);
  }

  const data = await res.json();
  return data.content?.[0]?.text ?? '';
}

function parseJson(raw) {
  // Strip markdown fences if present
  const cleaned = raw
    .replace(/^```(?:json)?\s*/i, '')
    .replace(/\s*```$/, '')
    .trim();
  return JSON.parse(cleaned);
}

async function callWithRetry(fn, retries = 1) {
  try {
    return await fn();
  } catch (err) {
    if (retries > 0) {
      await new Promise(r => setTimeout(r, 1500));
      return callWithRetry(fn, retries - 1);
    }
    throw err;
  }
}

// ── Step 1: Extract label data from image ──────────────────────────────────

export async function extractLabel(apiKey, imageBase64, mimeType) {
  const content = [
    {
      type: 'image',
      source: { type: 'base64', media_type: mimeType, data: imageBase64 },
    },
    {
      type: 'text',
      text: 'Extract all food label data from this image and return the JSON as instructed.',
    },
  ];

  const raw = await callWithRetry(() =>
    callClaude(apiKey, EXTRACTION_SYSTEM_PROMPT, content, 4096)
  );

  try {
    return parseJson(raw);
  } catch (e) {
    throw new Error(`Could not parse extraction response as JSON.\n\nRaw response:\n${raw}`);
  }
}

// ── Step 2: Convert to FDA format and run compliance checks ────────────────

export async function convertLabel(apiKey, extractedData) {
  const content = [
    {
      type: 'text',
      text: `Here is the extracted food label data:\n\n${JSON.stringify(extractedData, null, 2)}\n\nApply all FDA rules, convert every field, run all 30 compliance checks, and return the JSON as instructed.`,
    },
  ];

  const raw = await callWithRetry(() =>
    callClaude(apiKey, CONVERSION_SYSTEM_PROMPT, content, 8192)
  );

  try {
    return parseJson(raw);
  } catch (e) {
    throw new Error(`Could not parse conversion response as JSON.\n\nRaw response:\n${raw}`);
  }
}
