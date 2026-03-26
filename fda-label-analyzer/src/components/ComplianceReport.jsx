import React from 'react';

function Badge({ status }) {
  if (status === 'pass')    return <span className="badge badge-pass">✅ PASS</span>;
  if (status === 'warning') return <span className="badge badge-warning">⚠️ WARNING</span>;
  if (status === 'blocker') return <span className="badge badge-blocker">🚫 BLOCKER</span>;
  return <span className="badge">{status}</span>;
}

export default function ComplianceReport({ report }) {
  if (!report) return null;

  const { summary, items } = report;
  const blockerItems = items.filter(i => i.status === 'blocker');

  return (
    <div>
      {/* Summary banner */}
      <div className="summary-banner">
        <span className="banner-pill banner-green">✅ {summary.pass} Passed</span>
        <span className="banner-pill banner-amber">⚠️ {summary.warnings} Warnings</span>
        <span className="banner-pill banner-red">🚫 {summary.blockers} Blockers</span>
      </div>

      {/* Blocker alert */}
      {blockerItems.length > 0 && (
        <div className="blocker-alert">
          <h3>🚫 This label cannot enter the US market until the following issues are resolved:</h3>
          <ul>
            {blockerItems.map((b, i) => (
              <li key={i}><strong>{b.check}</strong> — {b.detail}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Full table */}
      <div style={{ overflowX: 'auto' }}>
        <table className="compliance-table">
          <thead>
            <tr>
              <th style={{ width: 36 }}>#</th>
              <th style={{ width: 160 }}>Status</th>
              <th>Compliance Check</th>
              <th>Detail</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item, i) => (
              <tr key={i}>
                <td style={{ color: 'var(--gray-600)', fontSize: '0.8rem' }}>{i + 1}</td>
                <td><Badge status={item.status} /></td>
                <td style={{ fontWeight: 500 }}>{item.check}</td>
                <td style={{ color: 'var(--gray-600)' }}>{item.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
