import React, { useState, useRef, useCallback } from 'react';

const ACCEPTED = '.jpg,.jpeg,.png,.webp,.gif,.pdf';
const MAX_MB = 20;

export default function UploadScreen({ onAnalyze }) {
  const [file, setFile]         = useState(null);
  const [preview, setPreview]   = useState(null); // data URL for image, null for PDF
  const [apiKey, setApiKey]     = useState(() => localStorage.getItem('fda_api_key') || '');
  const [showKey, setShowKey]   = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError]       = useState('');
  const inputRef = useRef(null);

  const handleFile = useCallback((f) => {
    setError('');
    if (!f) return;

    const mb = f.size / 1024 / 1024;
    if (mb > MAX_MB) {
      setError(`File is too large (${mb.toFixed(1)} MB). Maximum is ${MAX_MB} MB.`);
      return;
    }

    const isPdf = f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf');
    setFile(f);

    if (isPdf) {
      setPreview('pdf');
    } else {
      const reader = new FileReader();
      reader.onload = e => setPreview(e.target.result);
      reader.readAsDataURL(f);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleAnalyze = () => {
    if (!file)   { setError('Please select a label image or PDF.'); return; }
    if (!apiKey) { setError('Please enter your Anthropic API key.'); return; }
    localStorage.setItem('fda_api_key', apiKey);
    onAnalyze(file, apiKey);
  };

  return (
    <div className="upload-wrap">
      <div className="card">
        <h2 style={{ marginBottom: 6 }}>🇺🇸 FDA Label Analyzer</h2>
        <p style={{ color: 'var(--gray-600)', fontSize: '0.88rem', marginBottom: 20 }}>
          Upload a food label image or PDF — the app extracts all data,
          converts it to US FDA format, and generates a full compliance report.
        </p>

        {/* Drop zone */}
        <div
          className={`drop-zone${dragOver ? ' drag-over' : ''}`}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            onChange={e => handleFile(e.target.files?.[0])}
          />
          <div className="drop-icon">{file ? '📄' : '📤'}</div>
          {file ? (
            <>
              <h2>{file.name}</h2>
              <p>{(file.size / 1024).toFixed(0)} KB — Click to change</p>
            </>
          ) : (
            <>
              <h2>Drop your label here or click to browse</h2>
              <p>Accepts JPG, PNG, WEBP, GIF, PDF — max {MAX_MB} MB</p>
            </>
          )}
        </div>

        {/* Preview */}
        {preview && preview !== 'pdf' && (
          <div className="preview-wrap" style={{ marginTop: 12 }}>
            <span className="preview-label">Preview</span>
            <button className="remove-btn" onClick={e => { e.stopPropagation(); setFile(null); setPreview(null); }}>×</button>
            <img src={preview} alt="Label preview" />
          </div>
        )}
        {preview === 'pdf' && (
          <div className="preview-wrap" style={{ marginTop: 12, padding: 16, textAlign: 'center' }}>
            <span className="preview-label">PDF</span>
            <button className="remove-btn" onClick={e => { e.stopPropagation(); setFile(null); setPreview(null); }}>×</button>
            <div style={{ fontSize: '2rem', padding: 16 }}>📄</div>
            <p style={{ fontSize: '0.85rem', color: 'var(--gray-600)' }}>{file?.name}</p>
          </div>
        )}

        {/* API key */}
        <div className="api-key-row">
          <label htmlFor="api-key">Anthropic API Key</label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              id="api-key"
              type={showKey ? 'text' : 'password'}
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="sk-ant-..."
              autoComplete="off"
              spellCheck={false}
            />
            <button
              className="btn btn-secondary"
              style={{ padding: '9px 14px', flexShrink: 0 }}
              onClick={() => setShowKey(v => !v)}
            >
              {showKey ? '🙈' : '👁️'}
            </button>
          </div>
          <span className="api-key-hint">
            Your key is stored in localStorage and never sent anywhere except Anthropic's API.
          </span>
        </div>

        {/* Error */}
        {error && (
          <div className="error-box" style={{ marginTop: 14 }}>
            <p>⚠️ {error}</p>
          </div>
        )}

        {/* Analyze button */}
        <button
          className="btn btn-primary btn-full"
          onClick={handleAnalyze}
          disabled={!file || !apiKey}
        >
          🔍 Analyze Label
        </button>
      </div>
    </div>
  );
}
