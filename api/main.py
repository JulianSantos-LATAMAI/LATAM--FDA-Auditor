"""
VeriLabel FastAPI Backend v1.0
==============================
Exposes your FDA label conversion logic as a clean REST API.
Called by n8n, WhatsApp handler, web portal, or anything else.

Endpoints:
  POST /convert     — image → FDA label (JSON + HTML + PDF)
  POST /audit       — image → compliance report (JSON)
  GET  /health      — uptime check for deployment monitoring

Auth: API key in header  X-API-Key: your_secret_key
"""

import os
import re
import json
import base64
import logging
from io import BytesIO
from typing import Dict, List, Tuple, Optional

import openai
from fastapi import FastAPI, File, UploadFile, Header, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import weasyprint

# ============================================================================
# APP SETUP
# ============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verilabel")

app = FastAPI(
    title="VeriLabel API",
    description="LATAM → USA FDA Label Conversion Engine",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this when you go to production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# CONFIGURATION
# ============================================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
VERILABEL_API_KEY = os.environ.get("VERILABEL_API_KEY", "changeme-set-this-in-env")
MODEL = "gpt-4o"

openai.api_key = OPENAI_API_KEY


# ============================================================================
# AUTH
# ============================================================================

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != VERILABEL_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class ConversionResponse(BaseModel):
    success: bool
    product_name: Optional[str]
    serving_size: Optional[str]
    servings_per_container: Optional[str]
    warnings: List[str]
    errors: List[str]
    nutrition_data: Dict
    percent_dv: Dict
    html_label: str
    pdf_base64: str          # Base64-encoded PDF — decode in n8n to attach
    servings_flag: Optional[str]   # Human-readable explanation for ⚠ VERIFY
    missing_fields: List[str]      # Fields not on source label


class AuditResponse(BaseModel):
    success: bool
    compliance_score: int
    export_ready: bool
    status: str
    critical_issues: List[Dict]
    major_issues: List[Dict]
    minor_issues: List[Dict]
    passed_checks: List[str]
    changes_needed: List[str]
    detected_allergens: Dict


# ============================================================================
# FDA LOGIC — EXTRACTED FROM YOUR STREAMLIT APP
# ============================================================================

NULLABLE_FIELDS = {'fiber_g', 'added_sugars_g', 'trans_fat_g', 'cholesterol_mg', 'total_sugars_g'}

FDA_DAILY_VALUES = {
    'total_fat': 78, 'saturated_fat': 20, 'cholesterol': 300, 'sodium': 2300,
    'total_carb': 275, 'fiber': 28, 'added_sugars': 50, 'protein': 50,
    'vitamin_d': 20, 'calcium': 1300, 'iron': 18, 'potassium': 4700
}

MEXICAN_VNR = {
    'vitamin_b1': 1.4, 'vitamin_b2': 1.6, 'vitamin_b6': 1.7, 'vitamin_b12': 2.4,
    'vitamin_c': 90, 'vitamin_d': 5, 'vitamin_e': 15, 'calcium': 1000,
    'iron': 14, 'zinc': 15, 'iodine': 150, 'folic_acid': 400,
}


def apply_fda_rounding(value, nutrient_type: str) -> str:
    try:
        val = float(value)
    except (ValueError, TypeError):
        return "0"

    if nutrient_type == 'calories':
        if val < 5: return "0"
        elif val <= 50: return str(int(round(val / 5) * 5))
        else: return str(int(round(val / 10) * 10))

    elif nutrient_type in ['total_fat', 'saturated_fat', 'trans_fat']:
        if val < 0.5: return "0"
        elif val < 5:
            rounded = round(val * 2) / 2
            return str(int(rounded)) if rounded == int(rounded) else f"{rounded:.1f}"
        else: return str(int(round(val)))

    elif nutrient_type == 'cholesterol':
        if val < 2: return "0"
        elif val <= 5: return "5"
        else: return str(int(round(val / 5) * 5))

    elif nutrient_type == 'sodium':
        if val < 5: return "0"
        elif val <= 140: return str(int(round(val / 5) * 5))
        else: return str(int(round(val / 10) * 10))

    elif nutrient_type in ['total_carb', 'fiber', 'total_sugars', 'added_sugars', 'protein']:
        if val < 0.5: return "0"
        else: return str(int(round(val)))

    elif nutrient_type in ['vitamin_d_mcg', 'calcium_mg', 'iron_mg', 'potassium_mg']:
        if val < 0.5: return "0"
        return str(int(round(val)))

    return str(int(round(val)))


def calculate_percent_dv(nutrient: str, amount: float) -> int:
    if nutrient not in FDA_DAILY_VALUES or FDA_DAILY_VALUES[nutrient] == 0:
        return 0
    return round((amount / FDA_DAILY_VALUES[nutrient]) * 100)


def calculate_all_dv(data: Dict) -> Dict:
    mappings = {
        'total_fat': 'total_fat_g', 'saturated_fat': 'saturated_fat_g',
        'cholesterol': 'cholesterol_mg', 'sodium': 'sodium_mg',
        'total_carb': 'total_carb_g', 'fiber': 'fiber_g',
        'added_sugars': 'added_sugars_g', 'protein': 'protein_g',
        'vitamin_d': 'vitamin_d_mcg', 'calcium': 'calcium_mg',
        'iron': 'iron_mg', 'potassium': 'potassium_mg'
    }
    dv = {}
    for nutrient, field in mappings.items():
        try:
            val = data.get(field)
            amount = float(val) if val not in [None, '', 'null'] else 0
            dv[nutrient] = calculate_percent_dv(nutrient, amount)
        except (ValueError, TypeError):
            dv[nutrient] = 0
    return dv


def convert_metric_to_us_serving(metric_str: str) -> str:
    if not metric_str:
        return ''
    s = metric_str.strip().lower()

    # If already contains household measure, preserve it
    if any(w in s for w in ['cup', 'tbsp', 'tsp', 'oz', 'taza', 'cucharada', 'serving']):
        return metric_str

    conversions = {
        '1g': '1/4 tsp (1g)', '2g': '1/2 tsp (2g)', '3g': '1 tsp (3g)',
        '5g': '1 tsp (5g)', '15g': '1 tbsp (15g)', '28g': '1 oz (28g)',
        '30g': '2 tbsp (30g)', '24g': '2 tbsp (24g)', '50g': '1/4 cup (50g)',
        '100g': '3.5 oz (100g)', '240ml': '1 cup (240mL)', '250ml': '1 cup (250mL)',
        '100ml': '3.4 fl oz (100mL)', '120ml': '1/2 cup (120mL)',
        '15ml': '1 tbsp (15mL)', '5ml': '1 tsp (5mL)',
        '355ml': '12 fl oz (355mL)', '500ml': '2 cups (500mL)',
        '600ml': '20 fl oz (600mL)',
    }
    if s in conversions:
        return conversions[s]

    match = re.match(r'(\d+\.?\d*)\s*(g|ml)', s)
    if match:
        amount = float(match.group(1))
        unit = match.group(2)
        amount_display = str(int(amount)) if amount == int(amount) else str(amount)
        if unit == 'g':
            if amount <= 3: return f"1 tsp ({amount_display}g)"
            elif amount <= 15: return f"1 tbsp ({amount_display}g)"
            elif amount <= 30: return f"2 tbsp ({amount_display}g)"
            elif amount <= 100: return f"1/4 cup ({amount_display}g)"
            else:
                oz = round(amount / 28.35, 1)
                return f"{oz} oz ({amount_display}g)"
        elif unit == 'ml':
            if amount <= 15: return f"1 tbsp ({amount_display}mL)"
            elif amount <= 30: return f"2 tbsp ({amount_display}mL)"
            else:
                fl_oz = round(amount / 29.57, 1)
                return f"{fl_oz} fl oz ({amount_display}mL)"

    return f"1 serving ({metric_str})"


def build_serving_size_display(data: Dict) -> str:
    original = data.get('serving_size_original', '') or ''
    metric = data.get('serving_size_metric', '') or ''

    # Translate Spanish household terms
    if original and any(c in original.lower() for c in ['taza', 'cucharada', 'cucharadita', '(']):
        translated = original
        translated = re.sub(r'tazas? de té', 'cup of tea', translated, flags=re.IGNORECASE)
        translated = re.sub(r'tazas?', 'cup', translated, flags=re.IGNORECASE)
        translated = re.sub(r'cucharadas?', 'tbsp', translated, flags=re.IGNORECASE)
        translated = re.sub(r'cucharaditas?', 'tsp', translated, flags=re.IGNORECASE)
        return translated

    if metric:
        converted = convert_metric_to_us_serving(metric)
        if converted and '1 serving' not in converted:
            return converted

    return original or metric or 'SEE LABEL'


def resolve_servings_per_container(data: Dict) -> Tuple[str, Optional[str]]:
    """
    Returns (display_value, explanation_note)
    Tries extraction first, then calculation fallbacks.
    """
    spc = data.get('servings_per_container')

    if spc not in [None, '', 'null', 'None']:
        spc_str = str(spc).strip()
        if spc_str == '1':
            return ('1', 'Extracted as 1 — verify this is correct for a single-serve package')
        return (spc_str, None)

    # Fallback 1: container volume ÷ serving size
    container_ml = data.get('container_volume_ml')
    serving_ml = data.get('serving_size_ml')
    if container_ml and serving_ml:
        try:
            calc = round(float(container_ml) / float(serving_ml))
            note = f"Calculated from container size ({int(float(container_ml))}ml ÷ {int(float(serving_ml))}ml) — confirm before printing"
            return (f"About {calc}", note)
        except (ValueError, ZeroDivisionError):
            pass

    # Fallback 2: total calories ÷ calories per serving
    total_cal = data.get('total_calories_per_container')
    per_serving_cal = data.get('calories')
    if total_cal and per_serving_cal:
        try:
            calc = round(float(total_cal) / float(per_serving_cal))
            note = f"Calculated from total calories ({total_cal} ÷ {per_serving_cal} per serving) — confirm before printing"
            return (f"About {calc}", note)
        except (ValueError, ZeroDivisionError):
            pass

    return ('⚠ VERIFY', 'Servings not found on source label — enter manually before printing')


def validate_numeric_values(data: Dict) -> Dict:
    corrected = data.copy()

    # Flatten nutrition_facts if nested
    if 'nutrition_facts' in data and isinstance(data['nutrition_facts'], dict):
        nf = data['nutrition_facts']
        for key, value in nf.items():
            if key not in ['present', 'format', 'serving_size_original', 'serving_size_metric',
                           'serving_size_us', 'servings_per_container', 'vitamins_vnr_percent',
                           'total_calories_per_container', 'container_volume_ml', 'serving_size_ml']:
                corrected[key] = value
        corrected['serving_size_original'] = nf.get('serving_size_original', '')
        corrected['serving_size_metric'] = nf.get('serving_size_metric', '')
        corrected['servings_per_container'] = nf.get('servings_per_container')
        corrected['total_calories_per_container'] = nf.get('total_calories_per_container')
        corrected['container_volume_ml'] = nf.get('container_volume_ml')
        corrected['serving_size_ml'] = nf.get('serving_size_ml')

    numeric_fields = [
        'calories', 'total_fat_g', 'saturated_fat_g', 'trans_fat_g',
        'cholesterol_mg', 'sodium_mg', 'total_carb_g', 'fiber_g',
        'total_sugars_g', 'added_sugars_g', 'protein_g',
        'vitamin_d_mcg', 'calcium_mg', 'iron_mg', 'potassium_mg'
    ]

    for field in numeric_fields:
        val = corrected.get(field)
        if val is None or str(val).strip() in ['', 'null', 'None']:
            corrected[field] = None if field in NULLABLE_FIELDS else '0'
        else:
            try:
                fval = float(val)
                corrected[field] = str(max(0, fval))
            except (ValueError, TypeError):
                corrected[field] = None if field in NULLABLE_FIELDS else '0'

    return corrected


def convert_mexican_vitamins(corrected: Dict, original: Dict) -> Tuple[Dict, List[str]]:
    notes = []
    vnr_data = {}

    if 'nutrition_facts' in original and isinstance(original['nutrition_facts'], dict):
        vnr_data = original['nutrition_facts'].get('vitamins_vnr_percent', {})
    if not vnr_data:
        vnr_data = original.get('vitamins_vnr_percent', {})

    if not vnr_data or not any(v for v in vnr_data.values() if v):
        return corrected, notes

    notes.append("🇲🇽 Mexican VNR format detected — converting to FDA values")

    for nutrient, vnr_pct in vnr_data.items():
        if not vnr_pct or str(vnr_pct) in ['null', 'None', '']:
            continue
        try:
            pct = float(vnr_pct)
            if nutrient not in MEXICAN_VNR:
                continue
            absolute = (pct / 100) * MEXICAN_VNR[nutrient]
            if nutrient == 'calcium':
                corrected['calcium_mg'] = str(round(absolute, 1))
                notes.append(f"✓ Calcium: {pct}% VNR → {absolute:.1f}mg")
            elif nutrient == 'iron':
                corrected['iron_mg'] = str(round(absolute, 1))
                notes.append(f"✓ Iron: {pct}% VNR → {absolute:.1f}mg")
            elif nutrient == 'vitamin_d':
                corrected['vitamin_d_mcg'] = str(round(absolute, 1))
                notes.append(f"✓ Vitamin D: {pct}% VNR → {absolute:.1f}mcg")
            else:
                notes.append(f"✓ {nutrient}: {pct}% VNR → {absolute:.1f} (not required on FDA label)")
        except (ValueError, TypeError):
            pass

    return corrected, notes


def get_missing_fields(data: Dict) -> List[str]:
    """Return list of fields that are nullable and missing from source label."""
    missing = []
    labels = {
        'fiber_g': 'Dietary Fiber',
        'added_sugars_g': 'Added Sugars',
        'trans_fat_g': 'Trans Fat',
        'cholesterol_mg': 'Cholesterol',
        'total_sugars_g': 'Total Sugars',
    }
    for field, label in labels.items():
        if data.get(field) is None:
            missing.append(label)
    return missing


# ============================================================================
# HTML LABEL GENERATOR
# ============================================================================

def generate_fda_label_html(data: Dict, percent_dv: Dict,
                             spc_display: str, spc_note: Optional[str],
                             serving_size_display: str) -> str:

    def val(key, default='0'):
        v = data.get(key, default)
        return v if v not in [None, '', 'null'] else default

    def present(key):
        return data.get(key) not in [None, 'null', 'None', '']

    def dv(key):
        return percent_dv.get(key, 0)

    calories    = apply_fda_rounding(val('calories'), 'calories')
    total_fat   = apply_fda_rounding(val('total_fat_g'), 'total_fat')
    sat_fat     = apply_fda_rounding(val('saturated_fat_g'), 'saturated_fat')
    cholesterol = apply_fda_rounding(val('cholesterol_mg'), 'cholesterol')
    sodium      = apply_fda_rounding(val('sodium_mg'), 'sodium')
    total_carb  = apply_fda_rounding(val('total_carb_g'), 'total_carb')
    protein     = apply_fda_rounding(val('protein_g'), 'protein')
    vitamin_d   = apply_fda_rounding(val('vitamin_d_mcg'), 'vitamin_d_mcg')
    calcium     = apply_fda_rounding(val('calcium_mg'), 'calcium_mg')
    iron        = apply_fda_rounding(val('iron_mg'), 'iron_mg')
    potassium   = apply_fda_rounding(val('potassium_mg'), 'potassium_mg')

    # Trans fat
    trans_fat_row = ''
    if present('trans_fat_g'):
        tf = apply_fda_rounding(val('trans_fat_g'), 'trans_fat')
        trans_fat_row = f'<div class="nr i1"><div class="nl"><span class="na"><em>Trans</em> Fat {tf}g</span></div><div class="ndv"></div></div><div class="bt"></div>'
    else:
        trans_fat_row = '<div class="nr i1"><div class="nl"><span class="na"><em>Trans</em> Fat ?g</span></div><div class="ndv"></div></div><div class="bt"></div>'

    # Cholesterol
    if present('cholesterol_mg'):
        chol_row = f'<div class="nr"><div class="nl"><span class="nm">Cholesterol</span> <span class="na">{cholesterol}mg</span></div><div class="ndv">{dv("cholesterol")}%</div></div>'
    else:
        chol_row = '<div class="nr"><div class="nl"><span class="nm">Cholesterol</span> <span class="na">?mg</span></div><div class="ndv">?%</div></div>'

    # Fiber
    fiber_row = ''
    if present('fiber_g'):
        fiber = apply_fda_rounding(val('fiber_g'), 'fiber')
        fiber_row = f'<div class="nr i1"><div class="nl"><span class="na">Dietary Fiber {fiber}g</span></div><div class="ndv">{dv("fiber")}%</div></div><div class="bt"></div>'

    # Total sugars
    sugars_row = ''
    if present('total_sugars_g'):
        ts = apply_fda_rounding(val('total_sugars_g'), 'total_sugars')
        sugars_row = f'<div class="nr i1"><div class="nl"><span class="na">Total Sugars {ts}g</span></div><div class="ndv"></div></div><div class="bt"></div>'
    else:
        sugars_row = '<div class="nr i1"><div class="nl"><span class="na">Total Sugars ?g</span></div><div class="ndv"></div></div><div class="bt"></div>'

    # Added sugars — ALWAYS show (mandatory FDA field)
    if present('added_sugars_g'):
        ads = apply_fda_rounding(val('added_sugars_g'), 'added_sugars')
        added_sugars_row = f'<div class="nr i2"><div class="nl"><span class="na">Includes {ads}g Added Sugars</span></div><div class="ndv">{dv("added_sugars")}%</div></div><div class="bt"></div>'
    elif present('total_sugars_g') and val('total_sugars_g') == '0.0':
        added_sugars_row = '<div class="nr i2"><div class="nl"><span class="na">Includes 0g Added Sugars</span></div><div class="ndv">0%</div></div><div class="bt"></div>'
    else:
        added_sugars_row = '<div class="nr i2"><div class="nl"><span class="na required">Includes ?g Added Sugars ⚠</span></div><div class="ndv">?%</div></div><div class="bt"></div>'

    # Servings display
    spc_html = spc_display
    if spc_display == '⚠ VERIFY':
        spc_html = '<span style="color:#cc0000;font-weight:700;">⚠ VERIFY</span>'
    elif spc_note:
        spc_html = f'{spc_display} <span style="color:#cc0000;font-size:6pt;">*</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>FDA Nutrition Facts</title>
<style>
  @media print {{
    @page {{ margin: 0; }}
    body {{ margin: 8mm; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; background:#fff; line-height:1; }}
  .label {{ width:3.5in; border:1pt solid #000; padding:0.03in 0.08in; background:#fff; }}
  .title {{ font-size:32pt; font-weight:900; letter-spacing:-0.5pt; line-height:0.95; padding:2pt 0 1pt; }}
  .bk {{ height:12pt; background:#000; margin:0; }}
  .bm {{ height:6pt; background:#000; margin:0; }}
  .bt {{ height:1pt; background:#000; margin:0; }}
  .sv {{ padding:1pt 0; }}
  .sl {{ font-size:8.5pt; font-weight:700; line-height:1.1; padding:1pt 0; }}
  .sl span {{ font-weight:400; }}
  .aps {{ font-size:7.5pt; margin:2pt 0 0; }}
  .cc {{ display:flex; justify-content:space-between; align-items:baseline; }}
  .cl {{ font-size:11pt; font-weight:900; }}
  .cv {{ font-size:40pt; font-weight:900; line-height:0.9; letter-spacing:-1pt; }}
  .dvh {{ text-align:right; font-size:7pt; font-weight:700; margin:1pt 0 0; padding:1pt 0; }}
  .nr {{ display:flex; justify-content:space-between; align-items:baseline; font-size:8pt; padding:2pt 0 1pt; }}
  .nm {{ font-weight:900; }}
  .na {{ font-weight:400; }}
  .i1 {{ padding-left:10pt; }}
  .i2 {{ padding-left:20pt; }}
  .nl {{ flex:1; }}
  .ndv {{ font-weight:900; min-width:32pt; text-align:right; }}
  .required {{ color:#cc0000; }}
  .fn {{ font-size:6.5pt; line-height:1.25; margin:3pt 0 2pt; }}
</style>
</head>
<body>
<div class="label">
  <div class="title">Nutrition Facts</div>
  <div class="bt"></div>
  <div class="sv">
    <div class="sl"><strong>Servings per container</strong> <span>{spc_html}</span></div>
    <div class="sl"><strong>Serving size</strong> <span>{serving_size_display}</span></div>
  </div>
  <div class="bk"></div>
  <div class="aps">Amount per serving</div>
  <div class="cc">
    <div class="cl">Calories</div>
    <div class="cv">{calories}</div>
  </div>
  <div class="bm"></div>
  <div class="dvh">% Daily Value*</div>
  <div class="bt"></div>
  <div class="nr"><div class="nl"><span class="nm">Total Fat</span> <span class="na">{total_fat}g</span></div><div class="ndv">{dv('total_fat')}%</div></div>
  <div class="bt"></div>
  <div class="nr i1"><div class="nl"><span class="na">Saturated Fat {sat_fat}g</span></div><div class="ndv">{dv('saturated_fat')}%</div></div>
  <div class="bt"></div>
  {trans_fat_row}
  {chol_row}
  <div class="bt"></div>
  <div class="nr"><div class="nl"><span class="nm">Sodium</span> <span class="na">{sodium}mg</span></div><div class="ndv">{dv('sodium')}%</div></div>
  <div class="bt"></div>
  <div class="nr"><div class="nl"><span class="nm">Total Carbohydrate</span> <span class="na">{total_carb}g</span></div><div class="ndv">{dv('total_carb')}%</div></div>
  <div class="bt"></div>
  {fiber_row}
  {sugars_row}
  {added_sugars_row}
  <div class="nr"><div class="nl"><span class="nm">Protein</span> <span class="na">{protein}g</span></div><div class="ndv"></div></div>
  <div class="bk"></div>
  <div class="nr"><div class="nl"><span class="na">Vitamin D {vitamin_d}mcg</span></div><div class="ndv">{dv('vitamin_d')}%</div></div>
  <div class="bt"></div>
  <div class="nr"><div class="nl"><span class="na">Calcium {calcium}mg</span></div><div class="ndv">{dv('calcium')}%</div></div>
  <div class="bt"></div>
  <div class="nr"><div class="nl"><span class="na">Iron {iron}mg</span></div><div class="ndv">{dv('iron')}%</div></div>
  <div class="bt"></div>
  <div class="nr"><div class="nl"><span class="na">Potassium {potassium}mg</span></div><div class="ndv">{dv('potassium')}%</div></div>
  <div class="bk"></div>
  <div class="fn">* The % Daily Value (DV) tells you how much a nutrient in a serving of food contributes to a daily diet. 2,000 calories a day is used for general nutrition advice.</div>
</div>
</body>
</html>"""


def html_to_pdf_base64(html: str) -> str:
    """Convert HTML label to PDF and return as base64 string."""
    try:
        pdf_bytes = weasyprint.HTML(string=html).write_pdf()
        return base64.b64encode(pdf_bytes).decode('utf-8')
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return ""


# ============================================================================
# EXTRACTION PROMPTS
# ============================================================================

EXTRACTION_PROMPT = """You are an expert FDA nutrition label data extractor.
Extract ALL nutritional information from this LATAM food label with perfect accuracy.

CRITICAL RULES:
1. SERVINGS PER CONTAINER: Extract the EXACT number shown. NEVER default to 1 unless 
   explicitly stated. If not found, return null. Also extract:
   - total_calories_per_container: look for "por envase", "por botella", "per container"
   - container_volume_ml: from net quantity (e.g., 600 from "600ml")
   - serving_size_ml: numeric ml value of one serving if liquid

2. SERVING SIZE: Return the FULL text exactly as shown (e.g., "25g (1½ Taza de Té)").
   Also return serving_size_metric as just the metric portion.

3. DIETARY FIBER: Only extract if EXPLICITLY listed. If not shown → null. Never assume 0.

4. ADDED SUGARS: Only extract if EXPLICITLY listed. If not shown → null. Never infer.

5. TRANS FAT: Only extract if explicitly listed. If not shown → null.

6. CHOLESTEROL: Only extract if explicitly listed. If not shown → null.

7. TOTAL SUGARS: Only extract if explicitly listed. If not shown → null.

8. MEXICAN VNR: If vitamins show %VNR percentages, extract into vitamins_vnr_percent.

RETURN ONLY VALID JSON:
{
    "product_name": "string or null",
    "serving_size_original": "FULL text as shown",
    "serving_size_metric": "metric only e.g. 25g or 100ml",
    "serving_size_ml": "numeric ml value or null",
    "servings_per_container": "exact number or null — NEVER default to 1",
    "total_calories_per_container": "number or null",
    "container_volume_ml": "number or null",
    "calories": "number",
    "calories_raw": "unrounded number",
    "total_fat_g": "number",
    "saturated_fat_g": "number",
    "trans_fat_g": "number or null if not on label",
    "cholesterol_mg": "number or null if not on label",
    "sodium_mg": "number",
    "total_carb_g": "number",
    "fiber_g": "number or null if not on label",
    "total_sugars_g": "number or null if not on label",
    "added_sugars_g": "number or null if not on label — NEVER infer",
    "protein_g": "number",
    "vitamin_d_mcg": "number or null",
    "calcium_mg": "number or null",
    "iron_mg": "number or null",
    "potassium_mg": "number or null",
    "nutrition_facts": {
        "vitamins_vnr_percent": {
            "vitamin_b1": null, "vitamin_b2": null, "vitamin_b6": null,
            "vitamin_b12": null, "vitamin_c": null, "vitamin_d": null,
            "vitamin_e": null, "calcium": null, "iron": null,
            "zinc": null, "iodine": null, "folic_acid": null
        }
    }
}"""


# ============================================================================
# CORE PROCESSING FUNCTION
# ============================================================================

async def process_label_image(image_bytes: bytes, image_type: str) -> Dict:
    """Full pipeline: image → extracted data → validated → FDA label"""

    # 1. Call GPT-4o vision
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    image_data_url = f"data:{image_type};base64,{base64_image}"

    response = openai.ChatCompletion.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Extract all nutrition data from this LATAM label as JSON."},
                {"type": "image_url", "image_url": {"url": image_data_url, "detail": "high"}}
            ]}
        ],
        max_tokens=1500,
        temperature=0.0
    )

    raw_text = response['choices'][0]['message']['content']
    raw_text = raw_text.replace('```json', '').replace('```', '').strip()
    extracted = json.loads(raw_text)

    # 2. Validate and normalize numeric values
    validated = validate_numeric_values(extracted)

    # 3. Convert Mexican vitamins if present
    validated, vnr_notes = convert_mexican_vitamins(validated, extracted)

    # 4. Build serving size display
    serving_size_display = build_serving_size_display(validated)
    validated['serving_size_us'] = serving_size_display

    # 5. Resolve servings per container
    spc_display, spc_note = resolve_servings_per_container(validated)

    # 6. Calculate %DV
    percent_dv = calculate_all_dv(validated)
    validated['percent_dv'] = percent_dv

    # 7. Detect missing fields
    missing = get_missing_fields(validated)

    # 8. Build warnings list
    warnings = list(vnr_notes)
    calories_raw = validated.get('calories_raw') or validated.get('calories', '0')
    try:
        if float(calories_raw) > 0 and apply_fda_rounding(calories_raw, 'calories') == '0':
            warnings.append(f"⚠ Calories rounded to 0 per FDA rules — source shows {calories_raw} kcal. Compliant but verify with manufacturer.")
    except (ValueError, TypeError):
        pass
    if spc_note:
        warnings.append(f"⚠ Servings per container: {spc_note}")
    for field in missing:
        if field == 'Added Sugars':
            warnings.append("❌ Added Sugars is mandatory per 21 CFR 101.9(c)(6)(iii) — not found on source label. Obtain from manufacturer before printing.")
        else:
            warnings.append(f"⚠ {field} not found on source label — omitted or marked as unknown.")

    # 9. Generate HTML
    html = generate_fda_label_html(
        validated, percent_dv, spc_display, spc_note, serving_size_display
    )

    # 10. Generate PDF
    pdf_b64 = html_to_pdf_base64(html)

    return {
        "validated_data": validated,
        "percent_dv": percent_dv,
        "spc_display": spc_display,
        "spc_note": spc_note,
        "serving_size_display": serving_size_display,
        "html": html,
        "pdf_base64": pdf_b64,
        "warnings": warnings,
        "missing_fields": missing,
        "product_name": extracted.get('product_name'),
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0", "service": "VeriLabel API"}


@app.post("/convert", response_model=ConversionResponse)
async def convert_label(
    file: UploadFile = File(...),
    _: str = Depends(verify_api_key)
):
    """
    Convert a LATAM label image to an FDA-compliant Nutrition Facts panel.
    Returns JSON data, HTML label, and base64-encoded PDF.
    
    Use in n8n:
      - HTTP Request node → POST /convert
      - Header: X-API-Key: your_key
      - Body: form-data, field name "file", attach image
      - Response: parse json → use html_label or decode pdf_base64
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(status_code=400, detail="Only JPG and PNG images supported")

    image_bytes = await file.read()

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large — max 10MB")

    try:
        result = await process_label_image(image_bytes, file.content_type)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Could not parse nutrition data from image")
    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=502, detail=f"OpenAI error: {str(e)}")
    except Exception as e:
        logger.error(f"Conversion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    vd = result["validated_data"]

    return ConversionResponse(
        success=True,
        product_name=result.get("product_name"),
        serving_size=result["serving_size_display"],
        servings_per_container=result["spc_display"],
        warnings=result["warnings"],
        errors=[],
        nutrition_data=vd,
        percent_dv=result["percent_dv"],
        html_label=result["html"],
        pdf_base64=result["pdf_base64"],
        servings_flag=result.get("spc_note"),
        missing_fields=result["missing_fields"]
    )


@app.post("/audit", response_model=AuditResponse)
async def audit_label(
    file: UploadFile = File(...),
    _: str = Depends(verify_api_key)
):
    """
    Full FDA compliance audit of a complete label (not just nutrition panel).
    Returns compliance score, critical issues, and changes needed.
    """
    # Audit uses the complete label extraction prompt from your Streamlit app
    # Plug in your CompleteLabelValidator logic here — same pattern as /convert
    raise HTTPException(status_code=501, detail="Audit endpoint coming in v1.1 — use /convert for now")


# ============================================================================
# RUN LOCALLY
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
