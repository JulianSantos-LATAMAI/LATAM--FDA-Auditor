// Renders the first page of a PDF to a base64 PNG using PDF.js

let pdfjsLib = null;

async function getPdfjsLib() {
  if (pdfjsLib) return pdfjsLib;
  // Dynamically import so it doesn't block initial load
  pdfjsLib = await import('pdfjs-dist');
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;
  return pdfjsLib;
}

/**
 * Convert the first page of a PDF File to a base64 PNG string.
 * Returns { base64, mimeType }
 */
export async function pdfPageToBase64(file) {
  const lib = await getPdfjsLib();

  const arrayBuffer = await file.arrayBuffer();
  const pdf = await lib.getDocument({ data: arrayBuffer }).promise;
  const page = await pdf.getPage(1);

  const scale = 2; // higher = better quality for OCR
  const viewport = page.getViewport({ scale });

  const canvas = document.createElement('canvas');
  canvas.width = viewport.width;
  canvas.height = viewport.height;
  const ctx = canvas.getContext('2d');

  await page.render({ canvasContext: ctx, viewport }).promise;

  // Convert canvas → data URL → strip prefix → base64
  const dataUrl = canvas.toDataURL('image/png');
  const base64 = dataUrl.replace(/^data:image\/png;base64,/, '');

  return { base64, mimeType: 'image/png', canvas };
}

/**
 * Convert a regular image File to base64.
 * Returns { base64, mimeType }
 */
export function imageFileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      const [header, base64] = dataUrl.split(',');
      const mimeType = header.match(/data:([^;]+)/)[1];
      resolve({ base64, mimeType });
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/** Returns whether the file is a PDF */
export const isPdf = file => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
