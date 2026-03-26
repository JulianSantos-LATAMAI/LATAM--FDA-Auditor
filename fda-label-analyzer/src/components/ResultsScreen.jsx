import React, { useState } from 'react';
import ComplianceReport from './ComplianceReport.jsx';
import LabelOutput from './LabelOutput.jsx';

export default function ResultsScreen({ results, onReset }) {
  const [tab, setTab] = useState('compliance');

  const { compliance_report, us_label, conversion_notes } = results;
  const { summary } = compliance_report;

  return (
    <div className="results-wrap">
      {/* Header */}
      <div className="results-header">
        <div>
          <h2>Analysis Complete</h2>
          <p style={{ color: 'var(--gray-600)', fontSize: '0.88rem', marginTop: 2 }}>
            {summary.pass} passed · {summary.warnings} warnings · {summary.blockers} blockers
          </p>
        </div>
        <button className="btn btn-secondary" onClick={onReset}>
          ↩ Analyze Another Label
        </button>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button
          className={`tab-btn ${tab === 'compliance' ? 'active' : ''}`}
          onClick={() => setTab('compliance')}
        >
          ✅ Compliance Report ({summary.pass + summary.warnings + summary.blockers} checks)
        </button>
        <button
          className={`tab-btn ${tab === 'label' ? 'active' : ''}`}
          onClick={() => setTab('label')}
        >
          🇺🇸 US Label Output
        </button>
      </div>

      {/* Tab content */}
      <div className="card" style={{ padding: 24 }}>
        {tab === 'compliance' && (
          <ComplianceReport report={compliance_report} />
        )}
        {tab === 'label' && (
          <LabelOutput usLabel={us_label} conversionNotes={conversion_notes} />
        )}
      </div>
    </div>
  );
}
