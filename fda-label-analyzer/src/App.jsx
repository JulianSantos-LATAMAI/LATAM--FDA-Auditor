import React, { useState, useCallback } from 'react';
import UploadScreen from './components/UploadScreen.jsx';
import ProcessingScreen from './components/ProcessingScreen.jsx';
import ResultsScreen from './components/ResultsScreen.jsx';
import { extractLabel, convertLabel } from './utils/claudeApi.js';
import { imageFileToBase64, pdfPageToBase64, isPdf } from './utils/pdfUtils.js';

// Screens: 'upload' | 'processing' | 'results' | 'error'
export default function App() {
  const [screen, setScreen]           = useState('upload');
  const [processingStep, setStep]     = useState('read');
  const [results, setResults]         = useState(null);
  const [errorMsg, setErrorMsg]       = useState('');
  const [extractedData, setExtracted] = useState(null);

  const handleAnalyze = useCallback(async (file, apiKey) => {
    setScreen('processing');
    setErrorMsg('');

    try {
      // Step 1: Read file
      setStep('read');
      let base64, mimeType;
      if (isPdf(file)) {
        ({ base64, mimeType } = await pdfPageToBase64(file));
      } else {
        ({ base64, mimeType } = await imageFileToBase64(file));
      }

      // Step 2: Extract with Claude Vision
      setStep('extract');
      const extracted = await extractLabel(apiKey, base64, mimeType);

      if (!extracted || typeof extracted !== 'object') {
        throw new Error('Label could not be fully read. Please upload a clearer image.');
      }
      setExtracted(extracted);

      // Step 3: Convert + compliance check
      setStep('convert');
      const converted = await convertLabel(apiKey, extracted);

      if (!converted?.compliance_report || !converted?.us_label) {
        throw new Error('Conversion response was incomplete. Please try again.');
      }

      // Step 4: Render
      setStep('render');
      await new Promise(r => setTimeout(r, 400)); // brief pause for UX

      setResults(converted);
      setScreen('results');

    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || 'An unexpected error occurred.');
      setScreen('error');
    }
  }, []);

  const handleReset = useCallback(() => {
    setScreen('upload');
    setResults(null);
    setExtracted(null);
    setErrorMsg('');
    setStep('read');
  }, []);

  const handleRetry = useCallback(() => {
    setScreen('upload');
    setErrorMsg('');
  }, []);

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <span style={{ fontSize: '1.6rem' }}>🇺🇸</span>
        <div>
          <h1>US FDA Food Label Analyzer &amp; Converter</h1>
          <p>Upload any label · Claude extracts and converts to FDA format · Full compliance report</p>
        </div>
      </header>

      {/* Main content */}
      <main className="app-main">
        {screen === 'upload' && (
          <UploadScreen onAnalyze={handleAnalyze} />
        )}

        {screen === 'processing' && (
          <ProcessingScreen currentStep={processingStep} />
        )}

        {screen === 'results' && results && (
          <ResultsScreen results={results} onReset={handleReset} />
        )}

        {screen === 'error' && (
          <div style={{ width: '100%', maxWidth: 560 }}>
            <div className="card">
              <h2 style={{ color: 'var(--red)', marginBottom: 12 }}>⚠️ Analysis Failed</h2>
              <div className="error-box">
                <p>{errorMsg}</p>
              </div>
              <p style={{ marginTop: 16, fontSize: '0.88rem', color: 'var(--gray-600)' }}>
                <strong>What to try:</strong>
                <br />• Upload a higher-resolution image of the label
                <br />• Make sure the label text is clearly visible and not blurry
                <br />• Check that your API key is valid and has available credits
                <br />• Try a different image file
              </p>
              <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                <button className="btn btn-primary" onClick={handleRetry} style={{ flex: 1 }}>
                  ↩ Try Again
                </button>
                {extractedData && (
                  <button className="btn btn-secondary" onClick={() => {
                    // Allow viewing extraction if conversion failed
                    const fallback = {
                      compliance_report: {
                        summary: { pass: 0, warnings: 1, blockers: 0 },
                        items: [{
                          check: 'Conversion step',
                          status: 'warning',
                          detail: 'Conversion failed — extraction data available below',
                        }]
                      },
                      us_label: null,
                      conversion_notes: ['Extraction succeeded but conversion failed. Raw extracted data: ' + JSON.stringify(extractedData, null, 2)]
                    };
                    setResults(fallback);
                    setScreen('results');
                  }} style={{ flex: 1 }}>
                    View Extracted Data
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{
        textAlign: 'center', padding: '14px 16px',
        fontSize: '0.75rem', color: 'var(--gray-600)',
        borderTop: '1px solid var(--gray-200)',
      }}>
        21 CFR Part 101 · FALCPA · 19 CFR 134 · Spain-US Chamber FDA Labeling Guide
        &nbsp;·&nbsp; Not a substitute for legal/regulatory counsel
      </footer>
    </div>
  );
}
