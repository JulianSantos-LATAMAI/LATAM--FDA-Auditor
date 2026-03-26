import React from 'react';

function NfRow({ label, amount, dv, bold = false, indent = 0, italic = false }) {
  const labelClass = [
    'nf-row-label',
    bold ? 'bold' : '',
    indent === 1 ? 'indent1' : '',
    indent === 2 ? 'indent2' : '',
    italic ? 'italic' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className="nf-row">
      <span className={labelClass}>
        {italic ? <><i>{label.split(' ')[0]}</i> {label.split(' ').slice(1).join(' ')}</> : label}
        {amount ? ` ${amount}` : ''}
      </span>
      {dv !== undefined && dv !== '' && (
        <span className="nf-row-dv">{dv}</span>
      )}
    </div>
  );
}

export default function NutritionFactsBox({ nf }) {
  if (!nf) return null;

  const {
    servings_per_container,
    serving_size,
    calories,
    total_fat,
    saturated_fat,
    trans_fat,
    cholesterol,
    sodium,
    total_carbohydrate,
    dietary_fiber,
    total_sugars,
    added_sugars,
    protein,
    vitamin_d,
    calcium,
    iron,
    potassium,
    footnote,
  } = nf;

  const dvPct = val => val?.dv_percent ? `${val.dv_percent}` : '';

  return (
    <div className="nf-box">
      <div className="nf-title">Nutrition Facts</div>
      <div className="nf-servings">{servings_per_container || '?'} servings per container</div>

      <div className="nf-srv-row">
        <span>Serving size</span>
        <span>{serving_size || '?'}</span>
      </div>

      {/* Calories section */}
      <div className="nf-calories-section">
        <div className="nf-cal-left">
          <div className="nf-aps">Amount per serving</div>
          <div className="nf-cal-label">Calories</div>
        </div>
        <div className="nf-cal-number">{calories ?? '?'}</div>
      </div>

      <div className="nf-dv-header">% Daily Value*</div>

      <NfRow label="Total Fat"    amount={total_fat?.amount}    dv={dvPct(total_fat)}    bold />
      <NfRow label="Saturated Fat" amount={saturated_fat?.amount} dv={dvPct(saturated_fat)} indent={1} />
      <NfRow label="Trans Fat"    amount={trans_fat?.amount}                              indent={1} italic />
      <NfRow label="Cholesterol"  amount={cholesterol?.amount}  dv={dvPct(cholesterol)}  bold />
      <NfRow label="Sodium"       amount={sodium?.amount}       dv={dvPct(sodium)}       bold />
      <NfRow label="Total Carbohydrate" amount={total_carbohydrate?.amount} dv={dvPct(total_carbohydrate)} bold />
      <NfRow label="Dietary Fiber" amount={dietary_fiber?.amount} dv={dvPct(dietary_fiber)} indent={1} />
      <NfRow label="Total Sugars" amount={total_sugars?.amount}                          indent={1} />

      {/* Added Sugars — extra indented */}
      <div className="nf-row">
        <span className="nf-row-label indent2">
          Includes {added_sugars?.amount ?? '?'} Added Sugars
        </span>
        <span className="nf-row-dv">{dvPct(added_sugars)}</span>
      </div>

      <NfRow label="Protein" amount={protein?.amount} bold />

      <div className="nf-thick-rule" />

      {/* Minerals grid */}
      <div className="nf-minerals">
        <div className="nf-mineral">
          Vitamin D {vitamin_d?.amount ?? '?'}&nbsp;&nbsp;
          <span className="nf-mineral-dv">{dvPct(vitamin_d)}</span>
        </div>
        <div className="nf-mineral">
          Calcium {calcium?.amount ?? '?'}&nbsp;&nbsp;
          <span className="nf-mineral-dv">{dvPct(calcium)}</span>
        </div>
        <div className="nf-mineral">
          Iron {iron?.amount ?? '?'}&nbsp;&nbsp;
          <span className="nf-mineral-dv">{dvPct(iron)}</span>
        </div>
        <div className="nf-mineral">
          Potassium {potassium?.amount ?? '?'}&nbsp;&nbsp;
          <span className="nf-mineral-dv">{dvPct(potassium)}</span>
        </div>
      </div>

      <div className="nf-footnote">
        *{footnote ?? 'The % Daily Value (DV) tells you how much a nutrient in a serving of food contributes to a daily diet. 2,000 calories a day is used for general nutrition advice.'}
      </div>
    </div>
  );
}
