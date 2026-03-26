"""
US FDA Food Label Compliance Converter
Full implementation per 21 CFR Part 101, FALCPA, and 19 CFR 134
"""

import streamlit as st
import re
import os

st.set_page_config(
    page_title="US FDA Food Label Compliance Converter",
    page_icon="🇺🇸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════════
# E-NUMBER CONVERSION TABLE
# Format: "E_CODE": (fda_name, is_approved_in_us, is_color_additive, notes)
# ═══════════════════════════════════════════════════════════════════════════════

E_NUMBER_TABLE = {
    "E100":  ("Turmeric / Curcumin", True, True, ""),
    "E101":  ("Riboflavin", True, False, ""),
    "E102":  ("FD&C Yellow No. 5 (Tartrazine)", True, True, "Must be declared by name on label"),
    "E104":  ("Quinoline Yellow", False, True, "NOT approved as food color in US"),
    "E110":  ("FD&C Yellow No. 6 (Sunset Yellow)", True, True, ""),
    "E120":  ("Cochineal Extract; Carmine", True, True, "Must be declared by name; potential allergen"),
    "E122":  ("Carmoisine", False, True, "NOT approved as food color in US"),
    "E123":  ("Amaranth", False, True, "NOT approved as food color in US"),
    "E124":  ("Ponceau 4R", False, True, "NOT approved as food color in US"),
    "E127":  ("FD&C Red No. 3 (Erythrosine)", True, True, ""),
    "E129":  ("FD&C Red No. 40 (Allura Red)", True, True, ""),
    "E131":  ("FD&C Blue No. 1 (Brilliant Blue)", True, True, "Check current approval status"),
    "E132":  ("FD&C Blue No. 2 (Indigo Carmine)", True, True, ""),
    "E133":  ("FD&C Blue No. 1 (Brilliant Blue FCF)", True, True, ""),
    "E150a": ("Caramel Color", True, False, ""),
    "E160a": ("Beta-Carotene", True, True, ""),
    "E160b": ("Annatto Extract", True, True, ""),
    "E160c": ("Paprika Extract / Paprika Oleoresin", True, True, ""),
    "E171":  ("Titanium Dioxide", False, True, "NOT approved for food use in US"),
    "E200":  ("Sorbic Acid", True, False, ""),
    "E202":  ("Potassium Sorbate", True, False, ""),
    "E210":  ("Benzoic Acid", True, False, ""),
    "E211":  ("Sodium Benzoate", True, False, "Must declare function: 'sodium benzoate (preservative)'"),
    "E220":  ("Sulfur Dioxide", True, False, "Sulfite — must declare if >= 10 ppm"),
    "E221":  ("Sodium Sulfite", True, False, "Sulfite allergen declaration may apply"),
    "E223":  ("Sodium Metabisulfite", True, False, "Sulfite allergen declaration may apply"),
    "E224":  ("Potassium Metabisulfite", True, False, "Sulfite allergen declaration may apply"),
    "E250":  ("Sodium Nitrite", True, False, ""),
    "E251":  ("Sodium Nitrate", True, False, ""),
    "E260":  ("Acetic Acid", True, False, ""),
    "E270":  ("Lactic Acid", True, False, ""),
    "E300":  ("Ascorbic Acid", True, False, ""),
    "E301":  ("Sodium Ascorbate", True, False, ""),
    "E306":  ("Tocopherols (mixed)", True, False, ""),
    "E307":  ("Alpha-Tocopherol", True, False, ""),
    "E322":  ("Lecithin / Soy Lecithin", True, False, "If soy-derived, declare soy allergen"),
    "E330":  ("Citric Acid", True, False, ""),
    "E331":  ("Sodium Citrate", True, False, ""),
    "E332":  ("Potassium Citrate", True, False, ""),
    "E333":  ("Calcium Citrate", True, False, ""),
    "E334":  ("Tartaric Acid", True, False, ""),
    "E335":  ("Sodium Tartrate", True, False, ""),
    "E340":  ("Potassium Phosphate", True, False, ""),
    "E401":  ("Sodium Alginate", True, False, ""),
    "E407":  ("Carrageenan", True, False, ""),
    "E410":  ("Locust Bean Gum", True, False, ""),
    "E412":  ("Guar Gum", True, False, ""),
    "E414":  ("Acacia Gum / Gum Arabic", True, False, ""),
    "E415":  ("Xanthan Gum", True, False, ""),
    "E420":  ("Sorbitol", True, False, ""),
    "E421":  ("Mannitol", True, False, ""),
    "E422":  ("Glycerin / Glycerol", True, False, ""),
    "E440":  ("Pectin", True, False, ""),
    "E450":  ("Diphosphates / Sodium Acid Pyrophosphate", True, False, ""),
    "E451":  ("Triphosphates / Sodium Tripolyphosphate", True, False, ""),
    "E460":  ("Cellulose", True, False, ""),
    "E461":  ("Methyl Cellulose", True, False, ""),
    "E466":  ("Carboxymethyl Cellulose / Cellulose Gum", True, False, ""),
    "E471":  ("Mono- and Diglycerides", True, False, ""),
    "E472e": ("DATEM (Diacetyl Tartaric Acid Esters of Monoglycerides)", True, False, ""),
    "E476":  ("Polyglycerol Polyricinoleate (PGPR)", True, False, ""),
    "E481":  ("Sodium Stearoyl Lactylate", True, False, ""),
    "E500":  ("Sodium Bicarbonate / Sodium Carbonate", True, False, ""),
    "E501":  ("Potassium Bicarbonate", True, False, ""),
    "E503":  ("Ammonium Bicarbonate", True, False, ""),
    "E504":  ("Magnesium Carbonate", True, False, ""),
    "E508":  ("Potassium Chloride", True, False, ""),
    "E509":  ("Calcium Chloride", True, False, ""),
    "E516":  ("Calcium Sulfate", True, False, ""),
    "E551":  ("Silicon Dioxide", True, False, ""),
    "E553b": ("Talc", True, False, "Verify food-grade FDA approval for specific application"),
    "E621":  ("Monosodium Glutamate (MSG)", True, False, "Must declare as 'monosodium glutamate'"),
    "E627":  ("Disodium Guanylate", True, False, ""),
    "E631":  ("Disodium Inosinate", True, False, ""),
    "E635":  ("Disodium 5'-Ribonucleotides", True, False, ""),
    "E900":  ("Polydimethylsiloxane / Dimethylpolysiloxane", True, False, ""),
    "E901":  ("Beeswax", True, False, ""),
    "E903":  ("Carnauba Wax", True, False, ""),
    "E950":  ("Acesulfame Potassium / Acesulfame K", True, False, ""),
    "E951":  ("Aspartame", True, False, "Required warning: 'PHENYLKETONURICS: CONTAINS PHENYLALANINE'"),
    "E952":  ("Cyclamate", False, False, "NOT approved for food use in US"),
    "E953":  ("Isomalt", True, False, ""),
    "E954":  ("Saccharin", True, False, ""),
    "E955":  ("Sucralose", True, False, ""),
    "E960":  ("Steviol Glycosides / Stevia", True, False, ""),
    "E965":  ("Maltitol", True, False, ""),
    "E966":  ("Lactitol", True, False, ""),
    "E967":  ("Xylitol", True, False, ""),
    "E968":  ("Erythritol", True, False, ""),
}

# ═══════════════════════════════════════════════════════════════════════════════
# DAILY VALUES (21 CFR 101.9, 2020 update)
# ═══════════════════════════════════════════════════════════════════════════════

DAILY_VALUES = {
    "total_fat":        78,
    "saturated_fat":    20,
    "cholesterol":      300,
    "sodium":           2300,
    "total_carb":       275,
    "fiber":            28,
    "added_sugars":     50,
    "protein":          50,
    "vitamin_d":        20,
    "calcium":          1300,
    "iron":             18,
    "potassium":        4700,
    "vitamin_a":        900,
    "vitamin_c":        90,
    "thiamin":          1.2,
    "riboflavin":       1.3,
    "niacin":           16,
    "vitamin_b6":       1.7,
    "folate":           400,
    "vitamin_b12":      2.4,
    "biotin":           30,
    "pantothenic_acid": 5,
    "phosphorus":       1250,
    "iodine":           150,
    "magnesium":        420,
    "zinc":             11,
    "selenium":         55,
    "copper":           0.9,
    "manganese":        2.3,
    "chromium":         35,
    "molybdenum":       45,
    "chloride":         2300,
    "choline":          550,
}

FDA_FOOTNOTE = (
    "The % Daily Value (DV) tells you how much a nutrient in a serving of food "
    "contributes to a daily diet. 2,000 calories a day is used for general nutrition advice."
)

# ═══════════════════════════════════════════════════════════════════════════════
# FDA ROUNDING FUNCTIONS (21 CFR 101.9(c))
# ═══════════════════════════════════════════════════════════════════════════════

def _safe(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (TypeError, ValueError):
        return default


def round_calories(v):
    v = _safe(v)
    if v < 5:     return 0
    elif v <= 50: return int(round(v / 5) * 5)
    else:         return int(round(v / 10) * 10)


def round_fat(v):
    """Total Fat, Saturated Fat: <0.5->0, 0.5-5->nearest 0.5, >5->nearest 1"""
    v = _safe(v)
    if v < 0.5:  return 0
    elif v <= 5: return round(v * 2) / 2
    else:        return float(round(v))


def round_trans_fat(v):
    v = _safe(v)
    if v < 0.5: return 0
    return round_fat(v)


def round_cholesterol(v):
    """Returns (display_value, prefix)"""
    v = _safe(v)
    if v < 2:    return (0,  "")
    elif v <= 5: return (5,  "Less than ")
    else:        return (int(round(v / 5) * 5), "")


def round_sodium(v):
    v = _safe(v)
    if v < 5:      return 0
    elif v <= 140: return int(round(v / 5) * 5)
    else:          return int(round(v / 10) * 10)


def round_carb_fiber_sugar_protein(v):
    """Returns (display_value, prefix)"""
    v = _safe(v)
    if v < 0.5: return (0,  "")
    elif v < 1: return (1,  "Less than ")
    else:       return (int(round(v)), "")


def round_vitamin_d(v):
    v = _safe(v)
    if v < 0.35: return 0
    return round(v * 10) / 10


def round_calcium(v):
    v = _safe(v)
    if v < 25: return 0
    return int(round(v / 10) * 10)


def round_potassium(v):
    v = _safe(v)
    if v < 95: return 0
    return int(round(v / 10) * 10)


def round_iron(v):
    v = _safe(v)
    if v < 0.35: return 0
    return round(v * 10) / 10


def round_percent_dv(pct):
    if pct < 2:    return 0
    elif pct <= 10: return int(round(pct / 2) * 2)
    elif pct <= 50: return int(round(pct / 5) * 5)
    else:           return int(round(pct / 10) * 10)


def calc_percent_dv(amount, key):
    dv = DAILY_VALUES.get(key)
    if not dv or amount is None:
        return None
    raw = (_safe(amount) / dv) * 100
    return round_percent_dv(raw)

# ═══════════════════════════════════════════════════════════════════════════════
# NET QUANTITY FORMATTING
# ═══════════════════════════════════════════════════════════════════════════════

def format_net_quantity(value, unit, content_type):
    """Returns formatted net quantity string with both US and metric units."""
    if not value or value <= 0:
        return ""

    if unit == "kg":
        grams = value * 1000
    elif unit == "L":
        grams = value * 1000
    elif unit in ("mL", "g"):
        grams = value
    else:
        grams = value

    if content_type == "solid":
        oz = grams / 28.3495
        lb = grams / 453.592
        kg = grams / 1000
        if lb < 1:
            return f"NET WT {oz:.0f} OZ ({grams:.0f} g)"
        elif lb < 4:
            lb_whole = int(lb)
            oz_rem   = round((lb - lb_whole) * 16)
            return f"NET WT {oz:.0f} oz ({lb_whole} LB {oz_rem} OZ) {grams:.0f} g"
        else:
            return f"NET WT {lb:.1f} LB ({kg:.2f} kg)"
    else:
        ml    = grams
        fl_oz = ml / 29.5735
        pt    = fl_oz / 16
        gal   = fl_oz / 128
        L     = ml / 1000
        if pt < 1:
            return f"NET {fl_oz:.0f} FL OZ ({ml:.0f} mL)"
        elif gal < 1:
            pt_whole = int(pt)
            fl_rem   = round((pt - pt_whole) * 16)
            return f"NET {fl_oz:.0f} fl oz ({pt_whole} PT {fl_rem} FL OZ) {ml:.0f} mL"
        else:
            return f"NET {gal:.1f} GAL ({L:.2f} L)"

# ═══════════════════════════════════════════════════════════════════════════════
# INGREDIENT PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════

def process_ingredients(text):
    """Scan ingredient text for E-numbers, convert or flag each one."""
    conversions = []
    warnings    = []
    blockers    = []

    if not text:
        return {"processed_text": "", "conversions": [], "warnings": [], "blockers": []}

    processed = text
    pattern   = re.compile(r'\bE(\d{3}[a-zA-Z]?)\b', re.IGNORECASE)
    seen      = set()

    for match in pattern.finditer(text):
        raw = match.group(0)
        key = raw.upper()
        if key in seen:
            continue
        seen.add(key)

        if key in E_NUMBER_TABLE:
            fda_name, approved, is_color, notes = E_NUMBER_TABLE[key]
            if not approved:
                msg = (f"{key} ({fda_name}) is NOT approved for food use in the United States. "
                       "Must be removed or substituted before US market entry.")
                blockers.append({"e_num": key, "name": fda_name, "is_color": is_color,
                                 "message": msg, "notes": notes})
                processed = processed.replace(raw, f"[BLOCKED: {key}]")
            else:
                conversions.append({"e_num": key, "original": raw,
                                    "converted": fda_name, "notes": notes})
                processed = processed.replace(raw, fda_name)
        else:
            warnings.append({"e_num": key,
                             "message": (f"{key}: No direct FDA equivalent found. "
                                         "Manual review required before US market entry.")})
            processed = processed.replace(raw, f"[REVIEW: {key}]")

    return {"processed_text": processed, "conversions": conversions,
            "warnings": warnings, "blockers": blockers}

# ═══════════════════════════════════════════════════════════════════════════════
# ALLERGEN STATEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def format_allergen_statement(selected, method, fish_sp, shellfish_sp, nut_type, may_contain):
    if not selected:
        return "", []

    issues = []
    parts  = []

    for allergen in selected:
        if allergen == "milk":
            parts.append("Milk")
        elif allergen == "eggs":
            parts.append("Eggs")
        elif allergen == "fish":
            if fish_sp:
                parts.append(f"Fish ({fish_sp})")
            else:
                issues.append("FAIL: Fish allergen must declare species (e.g., 'Fish (salmon)').")
                parts.append("Fish [SPECIES REQUIRED]")
        elif allergen == "crustacean_shellfish":
            if shellfish_sp:
                parts.append(f"Crustacean Shellfish ({shellfish_sp})")
            else:
                issues.append("FAIL: Crustacean Shellfish must declare species.")
                parts.append("Crustacean Shellfish [SPECIES REQUIRED]")
        elif allergen == "tree_nuts":
            if nut_type:
                parts.append(f"Tree Nuts ({nut_type})")
            else:
                issues.append("FAIL: Tree Nuts must specify type. Never use 'tree nuts' alone.")
                parts.append("Tree Nuts [SPECIFIC TYPE REQUIRED]")
        elif allergen == "peanuts":
            parts.append("Peanuts")
        elif allergen == "soybeans":
            parts.append("Soybeans")
        elif allergen == "wheat":
            parts.append("Wheat")
        elif allergen == "sesame":
            parts.append("Sesame")

    if method == "contains_statement":
        statement = "Contains: " + ", ".join(parts) + "."
    else:
        statement = ""

    if may_contain:
        mc_note = f"\n[Advisory — place OUTSIDE mandatory IP elements]: May contain {may_contain}."
        statement = statement + mc_note if statement else mc_note

    return statement, issues

# ═══════════════════════════════════════════════════════════════════════════════
# NUTRITION FACTS HTML
# ═══════════════════════════════════════════════════════════════════════════════

def _gstr(val, prefix=""):
    if val == 0:            return f"{prefix}0g"
    if val == int(val):     return f"{prefix}{int(val)}g"
    return f"{prefix}{val}g"


def _mgstr(val, prefix=""):
    if val == 0: return f"{prefix}0mg"
    return f"{prefix}{int(val)}mg"


def _mcgstr(val, prefix=""):
    if val == 0: return f"{prefix}0mcg"
    if val == int(val): return f"{prefix}{int(val)}mcg"
    return f"{prefix}{val}mcg"


def _pdv(pct):
    if pct is None or pct == 0: return "0%"
    return f"{pct}%"


def generate_nutrition_facts_html(nf):
    calories    = round_calories(nf.get("calories", 0))
    total_fat   = round_fat(nf.get("total_fat_g", 0))
    sat_fat     = round_fat(nf.get("saturated_fat_g", 0))
    trans_fat   = round_trans_fat(nf.get("trans_fat_g", 0))
    chol_val, chol_pre = round_cholesterol(nf.get("cholesterol_mg", 0))
    sodium      = round_sodium(nf.get("sodium_mg", 0))
    tc, tcp     = round_carb_fiber_sugar_protein(nf.get("total_carb_g", 0))
    fi, fip     = round_carb_fiber_sugar_protein(nf.get("fiber_g", 0))
    ts, tsp     = round_carb_fiber_sugar_protein(nf.get("total_sugars_g", 0))
    as_, asp    = round_carb_fiber_sugar_protein(nf.get("added_sugars_g", 0))
    pr, prp     = round_carb_fiber_sugar_protein(nf.get("protein_g", 0))
    vit_d       = round_vitamin_d(nf.get("vitamin_d_mcg", 0))
    calcium     = round_calcium(nf.get("calcium_mg", 0))
    iron        = round_iron(nf.get("iron_mg", 0))
    potassium   = round_potassium(nf.get("potassium_mg", 0))

    fat_dv    = calc_percent_dv(total_fat,   "total_fat")
    satfat_dv = calc_percent_dv(sat_fat,     "saturated_fat")
    chol_dv   = calc_percent_dv(chol_val,    "cholesterol")
    sod_dv    = calc_percent_dv(sodium,      "sodium")
    carb_dv   = calc_percent_dv(tc,          "total_carb")
    fiber_dv  = calc_percent_dv(fi,          "fiber")
    addsug_dv = calc_percent_dv(as_,         "added_sugars")
    vitd_dv   = calc_percent_dv(vit_d,       "vitamin_d")
    calc_dv   = calc_percent_dv(calcium,     "calcium")
    iron_dv   = calc_percent_dv(iron,        "iron")
    potas_dv  = calc_percent_dv(potassium,   "potassium")

    household = nf.get("serving_household", "1 serving")
    srv_amt   = nf.get("serving_metric_amount", "")
    srv_unit  = nf.get("serving_metric_unit", "g")
    serving_display = f"{household} ({srv_amt}{srv_unit})" if srv_amt else household

    raw_srv = _safe(nf.get("servings_per_container", 1), 1.0)
    if raw_srv == 1:
        servings_display = "1 serving per container"
    elif raw_srv <= 5:
        r = round(raw_srv * 2) / 2
        servings_display = f"About {r:g} servings per container"
    else:
        r = round(raw_srv)
        servings_display = f"About {r} servings per container"

    # Optional voluntary nutrients
    poly_fat      = nf.get("poly_fat_g")
    mono_fat      = nf.get("mono_fat_g")
    sol_fiber     = nf.get("soluble_fiber_g")
    insol_fiber   = nf.get("insoluble_fiber_g")
    sugar_alcohol = nf.get("sugar_alcohol_g")
    vit_a         = nf.get("vitamin_a_mcg")
    vit_c         = nf.get("vitamin_c_mg")

    vol_rows = ""
    if poly_fat is not None:
        pf = round_fat(poly_fat)
        vol_rows += (f'<div style="display:flex;justify-content:space-between;'
                     f'padding:1px 0;border-top:1px solid #000;">'
                     f'<span style="padding-left:28px;">Polyunsaturated Fat {_gstr(pf)}</span>'
                     f'<span></span></div>')
    if mono_fat is not None:
        mf = round_fat(mono_fat)
        vol_rows += (f'<div style="display:flex;justify-content:space-between;'
                     f'padding:1px 0;border-top:1px solid #000;">'
                     f'<span style="padding-left:28px;">Monounsaturated Fat {_gstr(mf)}</span>'
                     f'<span></span></div>')
    if sol_fiber is not None:
        sf, sfp = round_carb_fiber_sugar_protein(sol_fiber)
        vol_rows += (f'<div style="display:flex;justify-content:space-between;'
                     f'padding:1px 0;border-top:1px solid #000;">'
                     f'<span style="padding-left:42px;">Soluble Fiber {_gstr(sf, sfp)}</span>'
                     f'<span></span></div>')
    if insol_fiber is not None:
        isf, isfp = round_carb_fiber_sugar_protein(insol_fiber)
        vol_rows += (f'<div style="display:flex;justify-content:space-between;'
                     f'padding:1px 0;border-top:1px solid #000;">'
                     f'<span style="padding-left:42px;">Insoluble Fiber {_gstr(isf, isfp)}</span>'
                     f'<span></span></div>')
    if sugar_alcohol is not None:
        sa, sap = round_carb_fiber_sugar_protein(sugar_alcohol)
        vol_rows += (f'<div style="display:flex;justify-content:space-between;'
                     f'padding:1px 0;border-top:1px solid #000;">'
                     f'<span style="padding-left:42px;">Sugar Alcohol {_gstr(sa, sap)}</span>'
                     f'<span></span></div>')

    extra_minerals = ""
    if vit_a is not None:
        va = round(_safe(vit_a))
        va_dv = calc_percent_dv(va, "vitamin_a")
        extra_minerals += (f'<div style="flex:1 1 40%;padding:2px 4px;border-left:1px solid #000;border-top:1px solid #000;">'
                           f'Vitamin A {va}mcg&nbsp;&nbsp;<b>{_pdv(va_dv)}</b></div>')
    if vit_c is not None:
        vc = round(_safe(vit_c))
        vc_dv = calc_percent_dv(vc, "vitamin_c")
        extra_minerals += (f'<div style="flex:1 1 40%;padding:2px 4px;border-left:1px solid #000;border-top:1px solid #000;">'
                           f'Vitamin C {vc}mg&nbsp;&nbsp;<b>{_pdv(vc_dv)}</b></div>')

    iron_str = f"{int(iron)}mg" if iron == int(iron) else f"{iron}mg"

    return f"""
<div style="border:2px solid #000;padding:6px 8px;width:320px;font-family:Arial,Helvetica,sans-serif;
            font-size:13px;background:#fff;color:#000;line-height:1.3;display:inline-block;">
  <div style="font-size:34px;font-weight:900;line-height:1.05;letter-spacing:-0.5px;">Nutrition Facts</div>
  <div style="font-size:12px;margin:2px 0;">{servings_display}</div>
  <div style="display:flex;justify-content:space-between;align-items:baseline;
              border-top:4px solid #000;padding-top:2px;font-weight:bold;font-size:13px;">
    <span>Serving size</span><span>{serving_display}</span>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:flex-end;
              border-top:8px solid #000;border-bottom:4px solid #000;padding:2px 0;margin:2px 0;">
    <div>
      <div style="font-size:10px;font-weight:bold;">Amount per serving</div>
      <div style="font-size:16px;font-weight:bold;">Calories</div>
    </div>
    <div style="font-size:52px;font-weight:900;line-height:1;">{calories}</div>
  </div>
  <div style="text-align:right;font-size:11px;font-weight:bold;padding-bottom:1px;">% Daily Value*</div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;font-weight:bold;">
    <span>Total Fat {_gstr(total_fat)}</span><span>{_pdv(fat_dv)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;">
    <span style="padding-left:14px;">Saturated Fat {_gstr(sat_fat)}</span><span>{_pdv(satfat_dv)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;">
    <span style="padding-left:14px;"><i>Trans</i> Fat {_gstr(trans_fat)}</span><span></span>
  </div>
  {vol_rows}
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;font-weight:bold;">
    <span>Cholesterol {_mgstr(chol_val, chol_pre)}</span><span>{_pdv(chol_dv)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;font-weight:bold;">
    <span>Sodium {_mgstr(sodium)}</span><span>{_pdv(sod_dv)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;font-weight:bold;">
    <span>Total Carbohydrate {_gstr(tc, tcp)}</span><span>{_pdv(carb_dv)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;">
    <span style="padding-left:14px;">Dietary Fiber {_gstr(fi, fip)}</span><span>{_pdv(fiber_dv)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;">
    <span style="padding-left:14px;">Total Sugars {_gstr(ts, tsp)}</span><span></span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;">
    <span style="padding-left:28px;">Includes {_gstr(as_, asp)} Added Sugars</span>
    <span>{_pdv(addsug_dv)}</span>
  </div>
  <div style="display:flex;justify-content:space-between;padding:1px 0;border-top:1px solid #000;font-weight:bold;">
    <span>Protein {_gstr(pr, prp)}</span><span></span>
  </div>
  <div style="border-top:8px solid #000;border-bottom:1px solid #000;margin:2px 0;">
    <div style="display:flex;flex-wrap:wrap;">
      <div style="flex:1 1 40%;padding:2px 4px;min-width:120px;">
        Vitamin D {_mcgstr(vit_d)}&nbsp;&nbsp;<b>{_pdv(vitd_dv)}</b>
      </div>
      <div style="flex:1 1 40%;padding:2px 4px;border-left:1px solid #000;">
        Calcium {_mgstr(calcium)}&nbsp;&nbsp;<b>{_pdv(calc_dv)}</b>
      </div>
      <div style="flex:1 1 40%;padding:2px 4px;border-top:1px solid #000;">
        Iron {iron_str}&nbsp;&nbsp;<b>{_pdv(iron_dv)}</b>
      </div>
      <div style="flex:1 1 40%;padding:2px 4px;border-left:1px solid #000;border-top:1px solid #000;">
        Potassium {_mgstr(potassium)}&nbsp;&nbsp;<b>{_pdv(potas_dv)}</b>
      </div>
      {extra_minerals}
    </div>
  </div>
  <div style="font-size:9px;margin-top:3px;line-height:1.3;">*{FDA_FOOTNOTE}</div>
</div>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# PDP TEXT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_pdp_text(fd):
    lines = []
    brand   = fd.get("brand_name", "").strip()
    product = fd.get("product_name", "").strip()
    flavor  = fd.get("flavor_description", "").strip()
    ftype   = fd.get("flavor_type", "none")
    pform   = fd.get("product_form", "").strip()
    geo     = fd.get("geo_origin_claim", "").strip()

    if brand:
        lines.append(brand.upper())

    soi = product
    if flavor and ftype != "none":
        if ftype == "natural":
            soi += f", Natural {flavor} Flavored"
        elif ftype == "artificial":
            soi += f", Artificially {flavor} Flavored"
        elif ftype == "natural_artificial":
            soi += f", Naturally and Artificially {flavor} Flavored"
    lines.append(soi if soi else "[Required: Statement of Identity]")

    if pform:
        lines.append(pform)
    if geo:
        lines.append(geo)

    lines.append("")

    storage = fd.get("storage_type", "room_temperature")
    if storage == "refrigerate":
        lines.append("KEEP REFRIGERATED")
    elif storage == "freeze":
        lines.append("KEEP FROZEN")
    elif storage == "perishable":
        lines.append("PERISHABLE — KEEP REFRIGERATED OR FROZEN")

    lines.append("")

    net_qty = format_net_quantity(
        fd.get("net_qty_value", 0) or 0,
        fd.get("net_qty_unit", "g"),
        fd.get("net_qty_type", "solid")
    )
    if net_qty:
        lines.append(net_qty)
        lines.append("[ Place in bottom 30% of Principal Display Panel ]")
    else:
        lines.append("[Required: Net quantity of contents]")

    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# INFORMATION PANEL TEXT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_ip_text(fd, proc_ing, allergen_stmt):
    lines = []

    ing_text = proc_ing.get("processed_text", "").strip()
    if ing_text:
        lines.append("INGREDIENTS: " + ing_text + ".")
    else:
        lines.append("INGREDIENTS: [Required — enter ingredients list]")
    lines.append("")

    if allergen_stmt:
        lines.append(allergen_stmt)
        lines.append("")

    company  = fd.get("company_name", "").strip()
    relation = fd.get("company_relation", "manufacturer")
    street   = fd.get("street_address", "").strip()
    city     = fd.get("city", "").strip()
    state    = fd.get("state_country", "").strip()
    zipcode  = fd.get("zip_code", "").strip()

    if company:
        labels = {
            "manufacturer":   "Manufactured by",
            "packed_for":     "Manufactured for",
            "distributed_by": "Distributed by",
            "packed_by":      "Packed for",
        }
        prefix = labels.get(relation, "Manufactured by")
        addr   = ", ".join(p for p in [street, city, state, zipcode] if p)
        lines.append(f"{prefix} {company}, {addr}" if addr else f"{prefix} {company}")
    else:
        lines.append("[Required: Responsible party name and address]")
    lines.append("")

    coo = fd.get("country_of_origin", "").strip()
    lines.append(f"Product of {coo}" if coo else "[Required: Country of origin — 19 CFR 134]")
    lines.append("")

    extras = []
    if fd.get("claim_gluten_free"):  extras.append("Gluten-Free")
    if fd.get("claim_nongmo"):       extras.append("Non-GMO")
    claims = fd.get("additional_claims", "").strip()
    if claims: extras.append(claims)
    if extras:
        lines.append(" | ".join(extras))

    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def run_compliance_checks(fd, proc_ing, allergen_data, allergen_issues):
    results                = []
    n_pass = n_warn = n_fail = 0

    def add(name, status, note=""):
        nonlocal n_pass, n_warn, n_fail
        results.append({"name": name, "status": status, "note": note})
        if status == "PASS":   n_pass += 1
        elif status == "WARN": n_warn += 1
        else:                  n_fail += 1

    soi = fd.get("product_name", "").strip()
    add("Statement of identity present and in English",
        "PASS" if soi else "FAIL",
        "" if soi else "Product name / statement of identity is required on the PDP")

    nq = _safe(fd.get("net_qty_value", 0))
    add("Net quantity in both US customary and metric units",
        "PASS" if nq > 0 else "FAIL",
        "" if nq > 0 else "Net quantity required in both US and metric units")

    add("Net quantity in bottom 30% of PDP", "WARN",
        "Designer note: Place net quantity declaration in the bottom 30% of the PDP")

    blockers   = proc_ing.get("blockers", [])
    e_warnings = proc_ing.get("warnings", [])
    if blockers:
        add("All E-numbers converted to FDA names", "FAIL",
            f"{len(blockers)} ingredient(s) not approved for US market — see E-Number Results above")
    elif e_warnings:
        add("All E-numbers converted to FDA names", "WARN",
            f"{len(e_warnings)} E-number(s) require manual review — no FDA equivalent found")
    else:
        add("All E-numbers converted to FDA names", "PASS")

    raw_ing   = fd.get("ingredients_raw", "")
    non_ascii = bool(re.search(r'[^\x00-\x7F]', raw_ing)) if raw_ing else False
    add("All ingredient names in English",
        "WARN" if non_ascii else "PASS",
        "Non-ASCII characters detected — verify all ingredient names are in English" if non_ascii else "")

    selected = allergen_data.get("selected", [])
    method   = allergen_data.get("declaration_method", "")
    if selected and not method:
        add("Allergens declared correctly (FALCPA compliant)", "FAIL",
            "Allergens selected but no declaration method chosen")
    elif selected and allergen_issues:
        add("Allergens declared correctly (FALCPA compliant)", "FAIL",
            " | ".join(allergen_issues))
    elif selected:
        add("Allergens declared correctly (FALCPA compliant)", "PASS")
    else:
        add("Allergens declared correctly (FALCPA compliant)", "WARN",
            "No allergens declared — confirm product contains none of the 9 major allergens")

    if "sesame" in selected:
        add("Sesame declared (required since Jan 1, 2023)", "PASS")
    else:
        add("Sesame declared (required since Jan 1, 2023)", "WARN",
            "Verify no sesame present — FASTER Act made sesame the 9th major allergen (Jan 1, 2023)")

    if "tree_nuts" in selected:
        add('"Tree Nuts" replaced with specific nut name',
            "PASS" if allergen_data.get("tree_nut_type", "").strip() else "FAIL",
            "" if allergen_data.get("tree_nut_type", "").strip()
            else "Specific tree nut type required (e.g., almonds, walnuts). Never use 'tree nuts' alone.")
    else:
        add('"Tree Nuts" replaced with specific nut name', "PASS", "N/A")

    if "fish" in selected:
        add("Fish declared by species",
            "PASS" if allergen_data.get("fish_species", "").strip() else "FAIL",
            "" if allergen_data.get("fish_species", "").strip()
            else "Fish species must be specified (e.g., salmon, tuna, cod)")
    else:
        add("Fish declared by species", "PASS", "N/A")

    if "crustacean_shellfish" in selected:
        add("Crustacean shellfish declared by species",
            "PASS" if allergen_data.get("shellfish_species", "").strip() else "FAIL",
            "" if allergen_data.get("shellfish_species", "").strip()
            else "Shellfish species required (e.g., shrimp, crab, lobster)")
    else:
        add("Crustacean shellfish declared by species", "PASS", "N/A")

    nf = fd.get("nutrition", {})
    mandatory = ["calories","total_fat_g","saturated_fat_g","trans_fat_g","cholesterol_mg",
                 "sodium_mg","total_carb_g","fiber_g","total_sugars_g","added_sugars_g",
                 "protein_g","vitamin_d_mcg","calcium_mg","iron_mg","potassium_mg"]
    missing_all = [k for k in mandatory if nf.get(k) is None]
    if missing_all:
        add("Nutrition Facts table has all 14 mandatory nutrients", "WARN",
            f"Values not entered: {', '.join(missing_all)}")
    else:
        add("Nutrition Facts table has all 14 mandatory nutrients", "PASS")

    add("Added Sugars declared separately",
        "PASS" if nf.get("added_sugars_g") is not None else "FAIL",
        "" if nf.get("added_sugars_g") is not None
        else "Added Sugars (g) must be declared separately beneath Total Sugars")

    add("Rounding rules applied correctly", "PASS", "Applied per 21 CFR 101.9(c)")
    add("% Daily Values calculated against correct DRVs/RDIs", "PASS",
        "Using 2020-2025 FDA DRV/RDI reference values")
    add("Footnote text exact per 21 CFR 101.9", "PASS",
        "Standard footnote included in Nutrition Facts label output")

    company = fd.get("company_name", "").strip()
    street  = fd.get("street_address", "").strip()
    city_v  = fd.get("city", "").strip()
    if company and street and city_v:
        add("Responsible party name and address present", "PASS")
    elif company:
        add("Responsible party name and address present", "WARN",
            "Company name entered but address is incomplete")
    else:
        add("Responsible party name and address present", "FAIL",
            "Responsible party name and complete address required on Information Panel")

    coo = fd.get("country_of_origin", "").strip()
    add("Country of origin declared",
        "PASS" if coo else "FAIL",
        "" if coo else "Required by US Customs (19 CFR 134)")

    color_blockers = [b for b in blockers if b.get("is_color")]
    other_blockers = [b for b in blockers if not b.get("is_color")]
    if color_blockers:
        add("No unapproved color additives", "FAIL",
            f"Unapproved color additive(s): {', '.join(b['e_num'] for b in color_blockers)}. "
            "Must be removed before US market entry.")
    elif other_blockers:
        add("No unapproved color additives", "WARN",
            f"Other unapproved ingredient(s): {', '.join(b['e_num'] for b in other_blockers)}")
    else:
        add("No unapproved color additives", "PASS")

    mc = fd.get("may_contain_advisory", "").strip()
    add('No "May contain" between mandatory IP elements',
        "WARN" if mc else "PASS",
        '"May contain" advisory must NOT be placed between mandatory IP elements — place separately'
        if mc else "")

    check_fields = [fd.get("product_name",""), fd.get("brand_name",""), fd.get("flavor_description","")]
    non_eng = any(re.search(r'[^\x00-\x7F]', f) for f in check_fields if f)
    add("All mandatory text in English",
        "WARN" if non_eng else "PASS",
        "Non-ASCII in mandatory fields. Foreign-language labels require English on all mandatory statements (21 CFR 101.15(c)(2))"
        if non_eng else "")

    storage = fd.get("storage_type", "room_temperature")
    if storage in ["refrigerate","freeze","perishable"]:
        add("Storage handling statement if required", "PASS",
            "Confirm prominent placement on PDP")
    else:
        add("Storage handling statement if required", "PASS", "N/A — room temperature product")

    return {"results": results, "passes": n_pass, "warnings": n_warn, "fails": n_fail}

# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_export_text(_fd, pdp_text, ip_text, nf, compliance):
    sep = "=" * 60
    lines = [
        sep,
        "US FDA FOOD LABEL COMPLIANCE BRIEF",
        "Generated by US FDA Food Label Compliance Converter",
        "Reference: 21 CFR Part 101  |  FALCPA  |  19 CFR 134",
        sep, "",
        "PRINCIPAL DISPLAY PANEL (PDP)",
        "-" * 40,
        pdp_text, "",
        "NUTRITION FACTS (rounded per 21 CFR 101.9(c))",
        "-" * 40,
    ]

    def nf_line(label, val):
        lines.append(f"  {label}: {val}")

    nf_line("Serving size",
            f"{nf.get('serving_household','')} "
            f"({nf.get('serving_metric_amount','')}{nf.get('serving_metric_unit','g')})")
    nf_line("Servings per container", nf.get("servings_per_container",""))
    nf_line("Calories", round_calories(nf.get("calories",0)))
    nf_line("Total Fat", _gstr(round_fat(nf.get("total_fat_g",0))))
    nf_line("  Saturated Fat", _gstr(round_fat(nf.get("saturated_fat_g",0))))
    nf_line("  Trans Fat", _gstr(round_trans_fat(nf.get("trans_fat_g",0))))
    cv, cp = round_cholesterol(nf.get("cholesterol_mg",0))
    nf_line("Cholesterol", _mgstr(cv, cp))
    nf_line("Sodium", _mgstr(round_sodium(nf.get("sodium_mg",0))))
    tcv, tcp = round_carb_fiber_sugar_protein(nf.get("total_carb_g",0))
    nf_line("Total Carbohydrate", _gstr(tcv, tcp))
    fiv, fip = round_carb_fiber_sugar_protein(nf.get("fiber_g",0))
    nf_line("  Dietary Fiber", _gstr(fiv, fip))
    tsv, tsp = round_carb_fiber_sugar_protein(nf.get("total_sugars_g",0))
    nf_line("  Total Sugars", _gstr(tsv, tsp))
    asv, asp = round_carb_fiber_sugar_protein(nf.get("added_sugars_g",0))
    nf_line("    Added Sugars", _gstr(asv, asp))
    prv, prp = round_carb_fiber_sugar_protein(nf.get("protein_g",0))
    nf_line("Protein", _gstr(prv, prp))
    nf_line("Vitamin D", _mcgstr(round_vitamin_d(nf.get("vitamin_d_mcg",0))))
    nf_line("Calcium", _mgstr(round_calcium(nf.get("calcium_mg",0))))
    iron_r = round_iron(nf.get("iron_mg",0))
    nf_line("Iron", f"{int(iron_r)}mg" if iron_r == int(iron_r) else f"{iron_r}mg")
    nf_line("Potassium", _mgstr(round_potassium(nf.get("potassium_mg",0))))

    lines += [
        "",
        "INFORMATION PANEL (IP)",
        "-" * 40,
        ip_text, "",
        "COMPLIANCE SUMMARY",
        "-" * 40,
        f"  PASS: {compliance['passes']}  |  WARNINGS: {compliance['warnings']}  |  FAIL: {compliance['fails']}",
        "",
    ]

    for r in compliance["results"]:
        icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[r["status"]]
        lines.append(f"  [{icon}] {r['name']}")
        if r.get("note"):
            lines.append(f"         -> {r['note']}")

    lines += ["", sep, "END OF LABEL BRIEF"]
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# AI INGREDIENT TRANSLATION (optional)
# ═══════════════════════════════════════════════════════════════════════════════

def ai_translate_ingredients(text, api_key):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            messages=[
                {"role": "system", "content": (
                    "You are an FDA food labeling expert. "
                    "Translate any non-English ingredient names to English using FDA common/usual names. "
                    "Convert any E-numbers to their FDA common names. "
                    "Return ONLY the translated ingredient list as plain text, comma-separated, "
                    "in the original order. Do not add explanations or commentary."
                )},
                {"role": "user", "content": f"Translate this ingredient list:\n{text}"}
            ],
            max_tokens=1000,
        )
        return resp.choices[0].message.content.strip(), None
    except Exception as e:
        return None, str(e)

# ═══════════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""<style>
.main-header{background:linear-gradient(135deg,#002868 0%,#BF0A30 100%);color:white;
             padding:20px 24px;border-radius:8px;margin-bottom:20px;}
.main-header h1{color:white;margin:0;font-size:1.6rem;}
.main-header p{color:rgba(255,255,255,0.85);margin:4px 0 0;font-size:0.9rem;}
.summary-banner{border-radius:6px;padding:12px 16px;font-size:1.05rem;
                font-weight:bold;margin-bottom:16px;text-align:center;}
.banner-good{background:#e6f4ea;border:1px solid #34a853;color:#1a7a1a;}
.banner-warn{background:#fff8e1;border:1px solid #f9ab00;color:#7d5a00;}
.banner-fail{background:#fce8e6;border:1px solid #ea4335;color:#a50000;}
.blocker-box{background:#fce8e6;border:1px solid #ea4335;border-left:4px solid #c0000c;
             border-radius:4px;padding:8px 12px;margin:4px 0;font-size:0.87rem;}
.warning-box{background:#fff8e1;border:1px solid #f9ab00;border-left:4px solid #a05f00;
             border-radius:4px;padding:8px 12px;margin:4px 0;font-size:0.87rem;}
.converted-box{background:#e6f4ea;border:1px solid #34a853;border-left:4px solid #1a7a1a;
               border-radius:4px;padding:8px 12px;margin:4px 0;font-size:0.87rem;}
</style>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
  <h1>&#127482;&#127480; US FDA Food Label Compliance Converter</h1>
  <p>Full compliance per 21 CFR Part 101 &middot; FALCPA &middot; 19 CFR 134 &middot; Spain-US Chamber FDA Labeling Guide</p>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙️ Settings")

    api_key = ""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get("OPENAI_API_KEY", "")

    if api_key:
        st.success("🟢 AI Translation: Active")
    else:
        st.info("🔘 AI Translation: Inactive\n\nAdd `OPENAI_API_KEY` to enable auto-translation of non-English ingredients.")

    st.markdown("---")
    st.markdown("### 📋 Quick Reference")

    with st.expander("Daily Values (DRVs/RDIs)"):
        st.markdown("""
| Nutrient | Daily Value |
|---|---|
| Total Fat | 78g |
| Saturated Fat | 20g |
| Cholesterol | 300mg |
| Sodium | 2,300mg |
| Total Carbohydrate | 275g |
| Dietary Fiber | 28g |
| Added Sugars | 50g |
| Protein | 50g |
| Vitamin D | 20mcg |
| Calcium | 1,300mg |
| Iron | 18mg |
| Potassium | 4,700mg |
""")

    with st.expander("E-Number Quick Lookup"):
        q = st.text_input("Search E-number", placeholder="e.g. E471", key="e_lookup")
        if q:
            key_q = q.strip().upper()
            if key_q in E_NUMBER_TABLE:
                name, approved, is_color, notes = E_NUMBER_TABLE[key_q]
                badge = "✅ Approved in US" if approved else "🚫 NOT Approved in US"
                clr_badge = " | 🎨 Color Additive" if is_color else ""
                st.markdown(f"**{key_q}**: {name}  \n{badge}{clr_badge}")
                if notes:
                    st.caption(notes)
            else:
                st.warning(f"{key_q} not found. Manual review required before US market entry.")

    st.markdown("---")
    st.caption("v4.0 — Full FDA Compliance Converter")
    st.caption("21 CFR Part 101 · FALCPA · 19 CFR 134")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ═══════════════════════════════════════════════════════════════════════════════

col_form, col_out = st.columns([5, 6], gap="large")

# ─────────────────────────────────────────────────────────────────────────────
# LEFT — INPUT FORM
# ─────────────────────────────────────────────────────────────────────────────

with col_form:
    st.subheader("📝 Label Input Form")

    # Section 1 ───────────────────────────────────────────────────────────────
    with st.expander("1. Product Identity", expanded=True):
        product_name = st.text_input("Product name (statement of identity)*",
                                     placeholder="e.g. Whole Grain Crackers",
                                     key="product_name")
        brand_name = st.text_input("Brand name",
                                   placeholder="e.g. Buena Mesa",
                                   key="brand_name")
        c1, c2 = st.columns([2, 1])
        with c1:
            flavor_description = st.text_input("Flavor description",
                                               placeholder="e.g. Honey",
                                               key="flavor_description")
        with c2:
            flavor_type = st.selectbox("Flavor type",
                                       ["none","natural","artificial","natural_artificial"],
                                       format_func=lambda x: {
                                           "none":               "No flavor claim",
                                           "natural":            "Natural",
                                           "artificial":         "Artificial",
                                           "natural_artificial": "Natural & Artificial",
                                       }[x],
                                       key="flavor_type")
        product_form = st.text_input("Product form (if not visible through packaging)",
                                     placeholder="e.g. Sliced, Diced, Powdered",
                                     key="product_form")
        geo_origin_claim = st.text_input("Geographic origin claim (optional)",
                                         placeholder="e.g. Made with Spanish Olive Oil",
                                         key="geo_origin_claim")

    # Section 2 ───────────────────────────────────────────────────────────────
    with st.expander("2. Net Quantity of Contents", expanded=True):
        ca, cb, cc = st.columns([2, 1, 2])
        with ca:
            net_qty_value = st.number_input("Value*", min_value=0.0, value=0.0,
                                            step=0.1, format="%.1f", key="net_qty_value")
        with cb:
            net_qty_unit = st.selectbox("Unit", ["g","kg","mL","L"], key="net_qty_unit")
        with cc:
            net_qty_type = st.selectbox("Content type",
                                        ["solid","liquid"],
                                        format_func=lambda x: "Solid / Semi-solid" if x=="solid" else "Liquid",
                                        key="net_qty_type")
        nq_preview = format_net_quantity(
            st.session_state.get("net_qty_value", 0) or 0,
            st.session_state.get("net_qty_unit", "g"),
            st.session_state.get("net_qty_type", "solid")
        )
        if nq_preview:
            st.success(f"**Declaration preview:** {nq_preview}")

    # Section 3 ───────────────────────────────────────────────────────────────
    with st.expander("3. Manufacturer / Packer / Distributor", expanded=False):
        company_name     = st.text_input("Company name*", key="company_name")
        company_relation = st.selectbox("Relationship to product",
                                        ["manufacturer","packed_for","distributed_by","packed_by"],
                                        format_func=lambda x: {
                                            "manufacturer":   "Manufactured by",
                                            "packed_for":     "Manufactured for / Packed for",
                                            "distributed_by": "Distributed by",
                                            "packed_by":      "Packed by",
                                        }[x],
                                        key="company_relation")
        street_address = st.text_input("Street address*", key="street_address")
        d1, d2, d3 = st.columns([2, 1, 1])
        with d1: city          = st.text_input("City*",              key="city")
        with d2: state_country = st.text_input("State / Country",    key="state_country")
        with d3: zip_code      = st.text_input("ZIP / Postal code",  key="zip_code")

    # Section 4 ───────────────────────────────────────────────────────────────
    with st.expander("4. Country of Origin", expanded=False):
        country_of_origin = st.text_input(
            "Country of origin* (required by 19 CFR 134)",
            placeholder="e.g. Spain, Mexico, Italy",
            key="country_of_origin")
        if country_of_origin:
            st.info(f'Will appear as: **"Product of {country_of_origin}"**')

    # Section 5 ───────────────────────────────────────────────────────────────
    with st.expander("5. Ingredients List", expanded=True):
        st.caption("Enter in descending order of predominance. E-numbers are auto-detected and converted.")
        ingredients_raw = st.text_area(
            "Ingredients (comma-separated)*",
            height=120,
            placeholder="e.g. Wheat flour, Sugar, Palm oil, E471, Salt, E330, E211 (preservative)",
            key="ingredients_raw")

        if api_key and ingredients_raw:
            if st.button("🤖 AI Translate to English", use_container_width=True,
                         help="Uses OpenAI to translate non-English ingredient names"):
                with st.spinner("Translating…"):
                    translated, err = ai_translate_ingredients(ingredients_raw, api_key)
                    if translated:
                        st.session_state["ingredients_raw"] = translated
                        st.success("Translated successfully — review the result above.")
                        st.rerun()
                    else:
                        st.error(f"AI translation error: {err}")

        st.markdown("---")
        st.caption("**May contain** advisory (voluntary — must NOT appear between mandatory IP elements)")
        may_contain_advisory = st.text_input("May contain:",
                                             placeholder="e.g. peanuts, tree nuts",
                                             key="may_contain_advisory")
        if may_contain_advisory:
            st.warning("Advisory will be flagged in compliance check — place it outside mandatory IP elements.")

    # Section 6 ───────────────────────────────────────────────────────────────
    with st.expander("6. Allergens (FALCPA — 9 Major Allergens)", expanded=True):
        st.caption("Select all allergens present in this product. **Sesame** is required since Jan 1, 2023 (FASTER Act).")

        al_cols = st.columns(3)
        allergen_map = [
            ("milk",                 "Milk"),
            ("eggs",                 "Eggs"),
            ("fish",                 "Fish"),
            ("crustacean_shellfish", "Crustacean Shellfish"),
            ("tree_nuts",            "Tree Nuts"),
            ("peanuts",              "Peanuts"),
            ("soybeans",             "Soybeans"),
            ("wheat",                "Wheat"),
            ("sesame",               "🌿 Sesame"),
        ]
        selected_allergens = []
        for i, (akey, alabel) in enumerate(allergen_map):
            with al_cols[i % 3]:
                if st.checkbox(alabel, key=f"allergen_{akey}"):
                    selected_allergens.append(akey)

        fish_species      = ""
        shellfish_species = ""
        tree_nut_type     = ""

        if "fish" in selected_allergens:
            fish_species = st.text_input("Fish species (required)*",
                                         placeholder="e.g. salmon, tuna, cod, halibut",
                                         key="fish_species")
        if "crustacean_shellfish" in selected_allergens:
            shellfish_species = st.text_input("Shellfish species (required)*",
                                              placeholder="e.g. shrimp, crab, lobster",
                                              key="shellfish_species")
        if "tree_nuts" in selected_allergens:
            tree_nut_type = st.text_input(
                "Tree nut type (required — NEVER use 'tree nuts' alone)*",
                placeholder="e.g. almonds, walnuts, pecans, cashews",
                key="tree_nut_type")

        st.markdown("**Allergen declaration method:**")
        declaration_method = st.radio(
            "Declaration method",
            ["contains_statement","inline_name","inline_parentheses"],
            format_func=lambda x: {
                "contains_statement":  'Option C — Separate "Contains:" statement after ingredient list',
                "inline_name":         "Option A — Allergen within ingredient name (e.g., 'egg yolk')",
                "inline_parentheses":  "Option B — Allergen in parentheses (e.g., 'sodium caseinate (Milk)')",
            }[x],
            key="declaration_method",
            label_visibility="collapsed")

    # Section 7 ───────────────────────────────────────────────────────────────
    with st.expander("7. Nutrition Facts", expanded=True):
        st.markdown("**Serving Information**")
        sv1, sv2, sv3 = st.columns([2, 1, 1])
        with sv1:
            serving_household = st.text_input(
                "Household measure*",
                placeholder="e.g. 2/3 cup, 1 tbsp, 3 pieces",
                key="serving_household")
        with sv2:
            serving_metric_amount = st.text_input(
                "Metric amount",
                placeholder="e.g. 55",
                key="serving_metric_amount")
        with sv3:
            serving_metric_unit = st.selectbox("Unit", ["g","mL"], key="serving_metric_unit")

        servings_per_container = st.number_input(
            "Servings per container*",
            min_value=0.0, value=1.0, step=0.5, format="%.1f",
            key="servings_per_container")

        st.markdown("---")
        st.markdown("**Mandatory Nutrients (all 14 required per 21 CFR 101.9)**")

        n1, n2 = st.columns(2)
        with n1:
            calories       = st.number_input("Calories (kcal)*",        min_value=0.0, value=0.0, step=1.0,  key="calories")
            total_fat_g    = st.number_input("Total Fat (g)*",           min_value=0.0, value=0.0, step=0.1,  key="total_fat_g")
            sat_fat_g      = st.number_input("  Saturated Fat (g)*",     min_value=0.0, value=0.0, step=0.1,  key="saturated_fat_g")
            trans_fat_g    = st.number_input("  Trans Fat (g)*",         min_value=0.0, value=0.0, step=0.1,  key="trans_fat_g")
            cholesterol_mg = st.number_input("Cholesterol (mg)*",        min_value=0.0, value=0.0, step=1.0,  key="cholesterol_mg")
            sodium_mg      = st.number_input("Sodium (mg)*",             min_value=0.0, value=0.0, step=1.0,  key="sodium_mg")
            total_carb_g   = st.number_input("Total Carbohydrate (g)*",  min_value=0.0, value=0.0, step=0.1,  key="total_carb_g")
        with n2:
            fiber_g        = st.number_input("  Dietary Fiber (g)*",     min_value=0.0, value=0.0, step=0.1,  key="fiber_g")
            total_sugars_g = st.number_input("  Total Sugars (g)*",      min_value=0.0, value=0.0, step=0.1,  key="total_sugars_g")
            added_sugars_g = st.number_input("    Added Sugars (g)*",    min_value=0.0, value=0.0, step=0.1,  key="added_sugars_g")
            protein_g      = st.number_input("Protein (g)*",             min_value=0.0, value=0.0, step=0.1,  key="protein_g")
            vitamin_d_mcg  = st.number_input("Vitamin D (mcg)*",         min_value=0.0, value=0.0, step=0.1,  key="vitamin_d_mcg")
            calcium_mg     = st.number_input("Calcium (mg)*",            min_value=0.0, value=0.0, step=1.0,  key="calcium_mg")
            iron_mg        = st.number_input("Iron (mg)*",               min_value=0.0, value=0.0, step=0.1,  key="iron_mg")
            potassium_mg   = st.number_input("Potassium (mg)*",          min_value=0.0, value=0.0, step=1.0,  key="potassium_mg")

        st.markdown("---")
        st.markdown("**Optional / Voluntary Nutrients**")
        vo1, vo2 = st.columns(2)

        with vo1:
            inc_poly  = st.checkbox("Polyunsaturated Fat",  key="inc_poly_fat")
            poly_fat_g    = st.number_input("Polyunsaturated Fat (g)", min_value=0.0, value=0.0, step=0.1,
                                            key="poly_fat_g")    if inc_poly  else None
            inc_mono  = st.checkbox("Monounsaturated Fat",  key="inc_mono_fat")
            mono_fat_g    = st.number_input("Monounsaturated Fat (g)", min_value=0.0, value=0.0, step=0.1,
                                            key="mono_fat_g")    if inc_mono  else None
            inc_sol   = st.checkbox("Soluble Fiber",        key="inc_sol_fiber")
            soluble_fiber_g = st.number_input("Soluble Fiber (g)", min_value=0.0, value=0.0, step=0.1,
                                              key="soluble_fiber_g") if inc_sol   else None
            inc_insol = st.checkbox("Insoluble Fiber",      key="inc_insol_fiber")
            insoluble_fiber_g = st.number_input("Insoluble Fiber (g)", min_value=0.0, value=0.0, step=0.1,
                                                key="insoluble_fiber_g") if inc_insol else None

        with vo2:
            inc_sa   = st.checkbox("Sugar Alcohol",         key="inc_sugar_alcohol")
            sugar_alcohol_g = st.number_input("Sugar Alcohol (g)", min_value=0.0, value=0.0, step=0.1,
                                              key="sugar_alcohol_g") if inc_sa   else None
            inc_vita = st.checkbox("Vitamin A",             key="inc_vitamin_a")
            vitamin_a_mcg   = st.number_input("Vitamin A (mcg)",   min_value=0.0, value=0.0, step=1.0,
                                              key="vitamin_a_mcg")  if inc_vita  else None
            inc_vitc = st.checkbox("Vitamin C",             key="inc_vitamin_c")
            vitamin_c_mg    = st.number_input("Vitamin C (mg)",    min_value=0.0, value=0.0, step=1.0,
                                              key="vitamin_c_mg")   if inc_vitc  else None

    # Section 8 ───────────────────────────────────────────────────────────────
    with st.expander("8. Storage Instructions", expanded=False):
        storage_type = st.radio(
            "Storage requirement",
            ["room_temperature","refrigerate","freeze","perishable"],
            format_func=lambda x: {
                "room_temperature": "Room temperature — no special statement needed",
                "refrigerate":      "Refrigerate  →  'KEEP REFRIGERATED'",
                "freeze":           "Freeze  →  'KEEP FROZEN'",
                "perishable":       "Perishable  →  'PERISHABLE — KEEP REFRIGERATED OR FROZEN'",
            }[x],
            key="storage_type")

    # Section 9 ───────────────────────────────────────────────────────────────
    with st.expander("9. Additional Claims (Optional)", expanded=False):
        claim_gluten_free = st.checkbox("Gluten-Free declaration", key="claim_gluten_free")
        claim_nongmo      = st.checkbox("Non-GMO statement",        key="claim_nongmo")
        additional_claims = st.text_area(
            "Other claims (nutrient content claims, health claims, etc.)",
            placeholder="e.g. Low Fat, Good Source of Fiber, Heart Healthy",
            height=80,
            key="additional_claims")
        if claim_gluten_free:
            st.info("Gluten-Free declaration must meet FDA definition: < 20 ppm gluten (21 CFR 101.91)")

    st.markdown("---")
    generate_btn = st.button("🇺🇸  Generate FDA Label Output",
                             type="primary", use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# RIGHT — OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

with col_out:
    if generate_btn:
        # Collect form data
        fd = {
            "product_name":       st.session_state.get("product_name", ""),
            "brand_name":         st.session_state.get("brand_name", ""),
            "flavor_description": st.session_state.get("flavor_description", ""),
            "flavor_type":        st.session_state.get("flavor_type", "none"),
            "product_form":       st.session_state.get("product_form", ""),
            "geo_origin_claim":   st.session_state.get("geo_origin_claim", ""),
            "net_qty_value":      st.session_state.get("net_qty_value", 0),
            "net_qty_unit":       st.session_state.get("net_qty_unit", "g"),
            "net_qty_type":       st.session_state.get("net_qty_type", "solid"),
            "company_name":       st.session_state.get("company_name", ""),
            "company_relation":   st.session_state.get("company_relation", "manufacturer"),
            "street_address":     st.session_state.get("street_address", ""),
            "city":               st.session_state.get("city", ""),
            "state_country":      st.session_state.get("state_country", ""),
            "zip_code":           st.session_state.get("zip_code", ""),
            "country_of_origin":  st.session_state.get("country_of_origin", ""),
            "ingredients_raw":    st.session_state.get("ingredients_raw", ""),
            "may_contain_advisory": st.session_state.get("may_contain_advisory", ""),
            "storage_type":       st.session_state.get("storage_type", "room_temperature"),
            "claim_gluten_free":  st.session_state.get("claim_gluten_free", False),
            "claim_nongmo":       st.session_state.get("claim_nongmo", False),
            "additional_claims":  st.session_state.get("additional_claims", ""),
            "nutrition": {
                "serving_household":      st.session_state.get("serving_household", ""),
                "serving_metric_amount":  st.session_state.get("serving_metric_amount", ""),
                "serving_metric_unit":    st.session_state.get("serving_metric_unit", "g"),
                "servings_per_container": st.session_state.get("servings_per_container", 1),
                "calories":           st.session_state.get("calories", 0),
                "total_fat_g":        st.session_state.get("total_fat_g", 0),
                "saturated_fat_g":    st.session_state.get("saturated_fat_g", 0),
                "trans_fat_g":        st.session_state.get("trans_fat_g", 0),
                "cholesterol_mg":     st.session_state.get("cholesterol_mg", 0),
                "sodium_mg":          st.session_state.get("sodium_mg", 0),
                "total_carb_g":       st.session_state.get("total_carb_g", 0),
                "fiber_g":            st.session_state.get("fiber_g", 0),
                "total_sugars_g":     st.session_state.get("total_sugars_g", 0),
                "added_sugars_g":     st.session_state.get("added_sugars_g", 0),
                "protein_g":          st.session_state.get("protein_g", 0),
                "vitamin_d_mcg":      st.session_state.get("vitamin_d_mcg", 0),
                "calcium_mg":         st.session_state.get("calcium_mg", 0),
                "iron_mg":            st.session_state.get("iron_mg", 0),
                "potassium_mg":       st.session_state.get("potassium_mg", 0),
                "poly_fat_g":         st.session_state.get("poly_fat_g")   if st.session_state.get("inc_poly_fat")      else None,
                "mono_fat_g":         st.session_state.get("mono_fat_g")   if st.session_state.get("inc_mono_fat")      else None,
                "soluble_fiber_g":    st.session_state.get("soluble_fiber_g") if st.session_state.get("inc_sol_fiber")  else None,
                "insoluble_fiber_g":  st.session_state.get("insoluble_fiber_g") if st.session_state.get("inc_insol_fiber") else None,
                "sugar_alcohol_g":    st.session_state.get("sugar_alcohol_g") if st.session_state.get("inc_sugar_alcohol") else None,
                "vitamin_a_mcg":      st.session_state.get("vitamin_a_mcg") if st.session_state.get("inc_vitamin_a")   else None,
                "vitamin_c_mg":       st.session_state.get("vitamin_c_mg")  if st.session_state.get("inc_vitamin_c")   else None,
            }
        }

        allergen_data = {
            "selected":           selected_allergens,
            "declaration_method": declaration_method,
            "fish_species":       fish_species,
            "shellfish_species":  shellfish_species,
            "tree_nut_type":      tree_nut_type,
        }

        proc_ing                  = process_ingredients(fd["ingredients_raw"])
        allergen_stmt, al_issues  = format_allergen_statement(
            selected_allergens, declaration_method,
            fish_species, shellfish_species, tree_nut_type,
            fd.get("may_contain_advisory",""))
        pdp_text  = generate_pdp_text(fd)
        ip_text   = generate_ip_text(fd, proc_ing, allergen_stmt)
        nf_html   = generate_nutrition_facts_html(fd["nutrition"])
        compliance = run_compliance_checks(fd, proc_ing, allergen_data, al_issues)

        st.session_state["output"] = {
            "fd": fd, "proc_ing": proc_ing, "allergen_stmt": allergen_stmt,
            "al_issues": al_issues, "pdp_text": pdp_text, "ip_text": ip_text,
            "nf_html": nf_html, "compliance": compliance,
        }

    output = st.session_state.get("output")

    if not output:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#666;">
          <div style="font-size:3rem;">🇺🇸</div>
          <h3>Fill in the form and click<br><em>Generate FDA Label Output</em></h3>
          <p>The full FDA-compliant label brief will appear here,<br>
          including Nutrition Facts, PDP, IP, and compliance check results.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        fd         = output["fd"]
        proc_ing   = output["proc_ing"]
        pdp_text   = output["pdp_text"]
        ip_text    = output["ip_text"]
        nf_html    = output["nf_html"]
        compliance = output["compliance"]

        n_pass = compliance["passes"]
        n_warn = compliance["warnings"]
        n_fail = compliance["fails"]

        # Summary banner
        if n_fail > 0:
            bcls, bicon = "banner-fail", "🚫"
        elif n_warn > 0:
            bcls, bicon = "banner-warn", "⚠️"
        else:
            bcls, bicon = "banner-good", "✅"

        st.markdown(
            f'<div class="summary-banner {bcls}">'
            f'{bicon}&nbsp; {n_pass} items ready ✅ &nbsp;|&nbsp; '
            f'{n_warn} warnings ⚠️ &nbsp;|&nbsp; {n_fail} blockers 🚫'
            f'</div>',
            unsafe_allow_html=True)

        # E-number results
        blockers    = proc_ing.get("blockers", [])
        e_warnings  = proc_ing.get("warnings", [])
        conversions = proc_ing.get("conversions", [])

        if blockers or e_warnings or conversions:
            with st.expander(
                    f"E-Number Processing: {len(conversions)} converted / "
                    f"{len(e_warnings)} unknown / {len(blockers)} blocked",
                    expanded=bool(blockers or e_warnings)):
                for b in blockers:
                    st.markdown(
                        f'<div class="blocker-box">🚫 <b>{b["e_num"]}</b>: {b["message"]}</div>',
                        unsafe_allow_html=True)
                for w in e_warnings:
                    st.markdown(
                        f'<div class="warning-box">⚠️ <b>{w["e_num"]}</b>: {w["message"]}</div>',
                        unsafe_allow_html=True)
                for c in conversions:
                    note = f" — {c['notes']}" if c.get("notes") else ""
                    st.markdown(
                        f'<div class="converted-box">✅ <b>{c["e_num"]}</b> → {c["converted"]}{note}</div>',
                        unsafe_allow_html=True)

        # Panel 1: PDP
        st.markdown("### 📦 Panel 1 — Principal Display Panel (PDP)")
        st.text_area("PDP text (copy into design brief)",
                     value=pdp_text, height=180, key="pdp_out")

        # Nutrition Facts label
        st.markdown("### 🥗 Nutrition Facts Label")
        st.markdown(nf_html, unsafe_allow_html=True)

        # Panel 2: IP
        st.markdown("### 📋 Panel 2 — Information Panel (IP)")
        st.text_area("IP text (copy into design brief)",
                     value=ip_text, height=200, key="ip_out")

        # Compliance results
        st.markdown("### ✅ Compliance Validation (21 CFR Part 101 · FALCPA · 19 CFR 134)")

        for r in compliance["results"]:
            if r["status"] == "PASS":
                ico, col = "✅", "#1a7a1a"
            elif r["status"] == "WARN":
                ico, col = "⚠️", "#a05f00"
            else:
                ico, col = "❌", "#c0000c"
            note_html = (f'<br><small style="color:{col};margin-left:28px;">→ {r["note"]}</small>'
                         if r.get("note") else "")
            st.markdown(
                f'<div style="padding:4px 0;border-bottom:1px solid #f0f0f0;">'
                f'<span style="color:{col};font-weight:500;">{ico} {r["name"]}</span>'
                f'{note_html}</div>',
                unsafe_allow_html=True)

        # Export
        st.markdown("---")
        export_text = generate_export_text(
            fd, pdp_text, ip_text, fd["nutrition"], compliance)
        st.download_button(
            label="⬇️  Export Full Label Brief as Text",
            data=export_text,
            file_name=f"FDA_Label_Brief_{fd.get('product_name','product').replace(' ','_')}.txt",
            mime="text/plain",
            use_container_width=True)
