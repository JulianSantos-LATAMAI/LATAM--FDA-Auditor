import React from 'react';

const STEPS = [
  { id: 'read',    label: 'Reading label file…' },
  { id: 'extract', label: 'Extracting label data with Claude Vision…' },
  { id: 'convert', label: 'Applying FDA rules & running compliance checks…' },
  { id: 'render',  label: 'Generating US-compliant label output…' },
];

export default function ProcessingScreen({ currentStep }) {
  const currentIdx = STEPS.findIndex(s => s.id === currentStep);

  return (
    <div className="processing-wrap">
      <div className="card" style={{ textAlign: 'center' }}>
        <div className="spinner" />
        <h2 style={{ marginBottom: 8 }}>Analyzing Label</h2>
        <p style={{ color: 'var(--gray-600)', fontSize: '0.88rem', marginBottom: 20 }}>
          This usually takes 15–30 seconds.
        </p>

        <ul className="steps">
          {STEPS.map((step, i) => {
            let state = 'pending';
            if (i < currentIdx)  state = 'done';
            if (i === currentIdx) state = 'active';

            return (
              <li key={step.id} className={`step ${state}`}>
                <span className="step-icon">
                  {state === 'done'   && '✅'}
                  {state === 'active' && '⏳'}
                  {state === 'pending'&& '○'}
                </span>
                <span className="step-text">{step.label}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
