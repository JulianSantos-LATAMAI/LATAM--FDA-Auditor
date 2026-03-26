import React, { useState } from 'react';
import NutritionFactsBox from './NutritionFactsBox.jsx';

function CopyBtn({ text, label = 'Copy' }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button className="btn btn-copy" onClick={handleCopy}>
      {copied ? '✅ Copied!' : `📋 ${label}`}
    </button>
  );
}

function buildPdpText(pdp) {
  const lines = [];
  if (pdp.statement_of_identity) lines.push(pdp.statement_of_identity.toUpperCase());
  if (pdp.storage_handling)      lines.push(pdp.storage_handling);
  if (pdp.net_quantity)          lines.push(`\n${pdp.net_quantity}`);
  return lines.join('\n');
}

function buildIpText(ip) {
  const lines = [];
  const nf = ip.nutrition_facts;
  if (nf) {
    lines.push('NUTRITION FACTS');
    lines.push(`${nf.servings_per_container} servings per container`);
    lines.push(`Serving size: ${nf.serving_size}`);
    lines.push(`Calories: ${nf.calories}`);
    lines.push(`Total Fat: ${nf.total_fat?.amount}  ${nf.total_fat?.dv_percent}`);
    lines.push(`  Saturated Fat: ${nf.saturated_fat?.amount}  ${nf.saturated_fat?.dv_percent}`);
    lines.push(`  Trans Fat: ${nf.trans_fat?.amount}`);
    lines.push(`Cholesterol: ${nf.cholesterol?.amount}  ${nf.cholesterol?.dv_percent}`);
    lines.push(`Sodium: ${nf.sodium?.amount}  ${nf.sodium?.dv_percent}`);
    lines.push(`Total Carbohydrate: ${nf.total_carbohydrate?.amount}  ${nf.total_carbohydrate?.dv_percent}`);
    lines.push(`  Dietary Fiber: ${nf.dietary_fiber?.amount}  ${nf.dietary_fiber?.dv_percent}`);
    lines.push(`  Total Sugars: ${nf.total_sugars?.amount}`);
    lines.push(`    Includes ${nf.added_sugars?.amount} Added Sugars  ${nf.added_sugars?.dv_percent}`);
    lines.push(`Protein: ${nf.protein?.amount}`);
    lines.push(`Vitamin D: ${nf.vitamin_d?.amount}  ${nf.vitamin_d?.dv_percent}`);
    lines.push(`Calcium: ${nf.calcium?.amount}  ${nf.calcium?.dv_percent}`);
    lines.push(`Iron: ${nf.iron?.amount}  ${nf.iron?.dv_percent}`);
    lines.push(`Potassium: ${nf.potassium?.amount}  ${nf.potassium?.dv_percent}`);
    lines.push(`*${nf.footnote}`);
    lines.push('');
  }
  if (ip.ingredients)        lines.push(`INGREDIENTS: ${ip.ingredients}`);
  if (ip.allergen_statement) lines.push(`\n${ip.allergen_statement}`);
  if (ip.responsible_party)  lines.push(`\n${ip.responsible_party}`);
  if (ip.country_of_origin)  lines.push(ip.country_of_origin);
  return lines.join('\n');
}

export default function LabelOutput({ usLabel, conversionNotes }) {
  if (!usLabel) return null;
  const { pdp, information_panel: ip } = usLabel;

  const pdpText  = buildPdpText(pdp);
  const ipText   = buildIpText(ip);
  const fullText = `US FDA-COMPLIANT LABEL BRIEF\n${'='.repeat(50)}\n\nPRINCIPAL DISPLAY PANEL\n${'-'.repeat(30)}\n${pdpText}\n\nINFORMATION PANEL\n${'-'.repeat(30)}\n${ipText}`;

  return (
    <div>
      <div className="label-panels">
        {/* PDP Panel */}
        <div className="label-panel">
          <div className="label-panel-header">
            <h3>📦 Principal Display Panel (PDP)</h3>
            <CopyBtn text={pdpText} label="Copy PDP" />
          </div>
          <div className="label-panel-body">
            {pdp.statement_of_identity && (
              <div className="pdp-product">{pdp.statement_of_identity}</div>
            )}
            {pdp.storage_handling && (
              <div className="pdp-storage">⚠️ {pdp.storage_handling}</div>
            )}
            {pdp.net_quantity && (
              <div className="pdp-net-qty">
                <strong>Net Quantity of Contents</strong>
                {pdp.net_quantity}
              </div>
            )}
            {!pdp.statement_of_identity && !pdp.net_quantity && (
              <p style={{ color: 'var(--gray-600)', fontSize: '0.88rem' }}>
                No PDP data extracted.
              </p>
            )}
          </div>
        </div>

        {/* IP Panel */}
        <div className="label-panel">
          <div className="label-panel-header">
            <h3>📋 Information Panel (IP)</h3>
            <CopyBtn text={ipText} label="Copy IP" />
          </div>
          <div className="label-panel-body">
            <NutritionFactsBox nf={ip.nutrition_facts} />

            {ip.ingredients && (
              <div className="ip-section">
                <div className="ip-label">Ingredients</div>
                <div className="ip-text">
                  <strong>INGREDIENTS:</strong> {ip.ingredients}
                </div>
              </div>
            )}

            {ip.allergen_statement && (
              <div className="ip-section">
                <div className="ip-text ip-contains">{ip.allergen_statement}</div>
              </div>
            )}

            {ip.responsible_party && (
              <div className="ip-section">
                <div className="ip-label">Responsible Party</div>
                <div className="ip-text">{ip.responsible_party}</div>
              </div>
            )}

            {ip.country_of_origin && (
              <div className="ip-section">
                <div className="ip-text">{ip.country_of_origin}</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Full export */}
      <div style={{ marginTop: 20, textAlign: 'center' }}>
        <CopyBtn text={fullText} label="Copy Full Label Brief" />
      </div>

      {/* Conversion notes */}
      {conversionNotes && conversionNotes.length > 0 && (
        <div className="conversion-notes card" style={{ marginTop: 24 }}>
          <h3>🔄 Conversion Notes</h3>
          {conversionNotes.map((note, i) => (
            <div key={i} className="note-item">
              <span>•</span>
              <span>{note}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
