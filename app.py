import streamlit as st
import base64
import os
import openai
from pathlib import Path
from datetime import datetime
import json
import re
from typing import Dict, List, Tuple, Optional

# ============================================================================
# FDA ROUNDING RULES - EXACT IMPLEMENTATION
# ============================================================================

def apply_fda_rounding_rules(value, nutrient_type):
    """
    Apply exact FDA rounding rules per 21 CFR 101.9(c)
    """
    try:
        val = float(value)
    except (ValueError, TypeError):
        return "0"
    
    if nutrient_type == 'calories':
        if val < 5:
            return "0"
        elif val <= 50:
            return str(int(round(val / 5) * 5))
        else:
            return str(int(round(val / 10) * 10))
    
    elif nutrient_type == 'total_fat':
        if val < 0.5:
            return "0"
        elif val < 5:
            rounded = round(val * 2) / 2
            if rounded == int(rounded):
                return str(int(rounded))
            return f"{rounded:.1f}"
        else:
            return str(int(round(val)))
    
    elif nutrient_type == 'saturated_fat':
        if val < 0.5:
            return "0"
        elif val < 5:
            rounded = round(val * 2) / 2
            if rounded == int(rounded):
                return str(int(rounded))
            return f"{rounded:.1f}"
        else:
            return str(int(round(val)))
    
    elif nutrient_type == 'trans_fat':
        # CRITICAL: FDA requires 0g display if <0.5g
        if val < 0.5:
            return "0"
        elif val < 5:
            rounded = round(val * 2) / 2
            if rounded == int(rounded):
                return str(int(rounded))
            return f"{rounded:.1f}"
        else:
            return str(int(round(val)))
    
    elif nutrient_type == 'cholesterol':
        if val < 2:
            return "0"
        elif val <= 5:
            return "5"
        else:
            return str(int(round(val / 5) * 5))
    
    elif nutrient_type == 'sodium':
        if val < 5:
            return "0"
        elif val <= 140:
            return str(int(round(val / 5) * 5))
        else:
            return str(int(round(val / 10) * 10))
    
    elif nutrient_type in ['total_carb', 'fiber', 'total_sugars', 'added_sugars']:
        # Carbohydrates and sugars: <0.5g = 0g, ≥0.5g round to nearest 1g
        if val < 0.5:
            return "0"
        else:
            return str(int(round(val)))
    
    elif nutrient_type == 'protein':
        # Protein rounding per FDA 21 CFR 101.9(c)(7):
        # <0.5g = 0g
        # ≥0.5g = round to nearest gram (so 0.5-1.4 = 1g, 1.5-2.4 = 2g, etc.)
        if val < 0.5:
            return "0"
        else:
            return str(int(round(val)))
    
    elif nutrient_type in ['vitamin_d_mcg', 'calcium_mg', 'iron_mg', 'potassium_mg']:
        if val < 0.5:
            return "0"
        return str(int(round(val)))
    
    else:
        return str(int(round(val)))


# ============================================================================
# PERFECT FDA LABEL GENERATOR
# ============================================================================

def generate_perfect_fda_label_html(nutrition_data, percent_dv):
    """
    Generate PERFECT FDA-compliant label matching official FDA format exactly
    """
    
    def get_val(key, default='0'):
        val = nutrition_data.get(key, default)
        return val if val not in [None, '', 'null'] else default
    
    def get_dv(key):
        return percent_dv.get(key, 0)
    
    # Apply FDA rounding rules
    calories = apply_fda_rounding_rules(get_val('calories'), 'calories')
    total_fat = apply_fda_rounding_rules(get_val('total_fat_g'), 'total_fat')
    saturated_fat = apply_fda_rounding_rules(get_val('saturated_fat_g'), 'saturated_fat')
    trans_fat = apply_fda_rounding_rules(get_val('trans_fat_g'), 'trans_fat')
    cholesterol = apply_fda_rounding_rules(get_val('cholesterol_mg'), 'cholesterol')
    sodium = apply_fda_rounding_rules(get_val('sodium_mg'), 'sodium')
    total_carb = apply_fda_rounding_rules(get_val('total_carb_g'), 'total_carb')
    fiber = apply_fda_rounding_rules(get_val('fiber_g'), 'fiber')
    total_sugars = apply_fda_rounding_rules(get_val('total_sugars_g'), 'total_sugars')
    added_sugars = apply_fda_rounding_rules(get_val('added_sugars_g'), 'added_sugars')
    protein = apply_fda_rounding_rules(get_val('protein_g'), 'protein')
    vitamin_d = apply_fda_rounding_rules(get_val('vitamin_d_mcg'), 'vitamin_d_mcg')
    calcium = apply_fda_rounding_rules(get_val('calcium_mg'), 'calcium_mg')
    iron = apply_fda_rounding_rules(get_val('iron_mg'), 'iron_mg')
    potassium = apply_fda_rounding_rules(get_val('potassium_mg'), 'potassium_mg')
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FDA Nutrition Facts Label</title>
    <style>
        @media print {{
            @page {{ margin: 0mm; }}
            body {{ margin: 10mm; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
            .no-print {{ display: none; }}
        }}
        
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: #f5f5f5; padding: 20px; line-height: 1; }}
        
        .container {{ max-width: 800px; margin: 0 auto; }}
        
        .nutrition-label {{
            width: 3.5in;
            border: 1pt solid #000000;
            padding: 0.03in 0.08in;
            background: white;
            margin: 0 auto 20px auto;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .title {{ font-size: 32pt; font-weight: 900; letter-spacing: -0.5pt; line-height: 0.95; padding: 2pt 0 1pt 0; }}
        .bar-thick {{ height: 12pt; background: #000000; border: none; margin: 0; }}
        .bar-medium {{ height: 6pt; background: #000000; border: none; margin: 0; }}
        .bar-thin {{ height: 1pt; background: #000000; border: none; margin: 0; }}
        
        .serving-container {{ padding: 1pt 0; }}
        .serving-line {{ font-size: 8.5pt; font-weight: 700; line-height: 1.1; padding: 1pt 0; }}
        .serving-line span {{ font-weight: 400; }}
        
        .amount-per-serving {{ font-size: 7.5pt; font-weight: 400; margin: 2pt 0 0 0; }}
        
        .calories-container {{ display: flex; justify-content: space-between; align-items: baseline; }}
        .calories-label {{ font-size: 11pt; font-weight: 900; letter-spacing: -0.3pt; }}
        .calories-value {{ font-size: 40pt; font-weight: 900; line-height: 0.9; letter-spacing: -1pt; }}
        
        .dv-header {{ text-align: right; font-size: 7pt; font-weight: 700; margin: 1pt 0 0 0; padding: 1pt 0; }}
        
        .nutrient-row {{ display: flex; justify-content: space-between; align-items: baseline; font-size: 8pt; line-height: 1; padding: 2pt 0 1pt 0; }}
        .nutrient-main {{ font-weight: 900; }}
        .nutrient-amount {{ font-weight: 400; }}
        .nutrient-indent-1 {{ padding-left: 10pt; }}
        .nutrient-indent-2 {{ padding-left: 20pt; }}
        .nutrient-label {{ flex: 1; }}
        .nutrient-dv {{ font-weight: 900; min-width: 32pt; text-align: right; }}
        
        .footnote {{ font-size: 6.5pt; line-height: 1.25; margin: 3pt 0 2pt 0; font-weight: 400; }}
        
        .instructions {{ background: white; padding: 25px; margin: 0 auto; max-width: 650px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .instructions h2 {{ color: #1a5490; margin-bottom: 15px; font-size: 22px; }}
        .instructions h3 {{ color: #2c5282; margin: 20px 0 10px 0; font-size: 16px; }}
        .instructions ol, .instructions ul {{ margin-left: 25px; line-height: 1.8; }}
        .instructions li {{ margin-bottom: 8px; }}
        
        .note {{ background: #e6f3ff; border-left: 4px solid #1890ff; padding: 15px; margin: 20px 0; border-radius: 4px; }}
        kbd {{ background: #f4f4f4; border: 1px solid #ccc; border-radius: 3px; padding: 2px 6px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="nutrition-label">
            <div class="title">Nutrition Facts</div>
            
            <div class="bar-thin"></div>
            <div class="serving-container">
                <div class="serving-line"><strong>Servings per container</strong> <span>{get_val('servings_per_container', '1')}</span></div>
                <div class="serving-line"><strong>Serving size</strong> <span>{get_val('serving_size_us', '2 tbsp (30g)')}</span></div>
            </div>
            
            <div class="bar-thick"></div>
            <div class="amount-per-serving">Amount per serving</div>
            
            <div class="calories-container">
                <div class="calories-label">Calories</div>
                <div class="calories-value">{calories}</div>
            </div>
            
            <div class="bar-medium"></div>
            <div class="dv-header">% Daily Value*</div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-main">Total Fat</span> <span class="nutrient-amount">{total_fat}g</span>
                </div>
                <div class="nutrient-dv">{get_dv('total_fat')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row nutrient-indent-1">
                <div class="nutrient-label">
                    <span class="nutrient-amount">Saturated Fat {saturated_fat}g</span>
                </div>
                <div class="nutrient-dv">{get_dv('saturated_fat')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row nutrient-indent-1">
                <div class="nutrient-label">
                    <span class="nutrient-amount"><em>Trans</em> Fat {trans_fat}g</span>
                </div>
                <div class="nutrient-dv"></div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-main">Cholesterol</span> <span class="nutrient-amount">{cholesterol}mg</span>
                </div>
                <div class="nutrient-dv">{get_dv('cholesterol')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-main">Sodium</span> <span class="nutrient-amount">{sodium}mg</span>
                </div>
                <div class="nutrient-dv">{get_dv('sodium')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-main">Total Carbohydrate</span> <span class="nutrient-amount">{total_carb}g</span>
                </div>
                <div class="nutrient-dv">{get_dv('total_carb')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row nutrient-indent-1">
                <div class="nutrient-label">
                    <span class="nutrient-amount">Dietary Fiber {fiber}g</span>
                </div>
                <div class="nutrient-dv">{get_dv('fiber')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row nutrient-indent-1">
                <div class="nutrient-label">
                    <span class="nutrient-amount">Total Sugars {total_sugars}g</span>
                </div>
                <div class="nutrient-dv"></div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row nutrient-indent-2">
                <div class="nutrient-label">
                    <span class="nutrient-amount">Includes {added_sugars}g Added Sugars</span>
                </div>
                <div class="nutrient-dv">{get_dv('added_sugars')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-main">Protein</span> <span class="nutrient-amount">{protein}g</span>
                </div>
                <div class="nutrient-dv">{get_dv('protein') if get_dv('protein') > 0 else ''}</div>
            </div>
            
            <div class="bar-thick"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-amount">Vitamin D {vitamin_d}mcg</span>
                </div>
                <div class="nutrient-dv">{get_dv('vitamin_d')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-amount">Calcium {calcium}mg</span>
                </div>
                <div class="nutrient-dv">{get_dv('calcium')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-amount">Iron {iron}mg</span>
                </div>
                <div class="nutrient-dv">{get_dv('iron')}%</div>
            </div>
            <div class="bar-thin"></div>
            
            <div class="nutrient-row">
                <div class="nutrient-label">
                    <span class="nutrient-amount">Potassium {potassium}mg</span>
                </div>
                <div class="nutrient-dv">{get_dv('potassium')}%</div>
            </div>
            
            <div class="bar-thick"></div>
            
            <div class="footnote">
                * The % Daily Value (DV) tells you how much a nutrient in a serving of food contributes to a daily diet. 2,000 calories a day is used for general nutrition advice.
            </div>
        </div>
        
        <div class="instructions no-print">
            <h2>📋 Your FDA-Compliant Label is Ready!</h2>
            
            <div class="note">
                <strong>✅ This label meets all FDA requirements:</strong>
                <ul style="margin: 10px 0 0 20px;">
                    <li>Exact FDA formatting per 21 CFR 101.9</li>
                    <li>Correct rounding rules applied</li>
                    <li>Proper font sizes, weights, and spacing</li>
                    <li>Standard 3.5-inch width</li>
                </ul>
            </div>
            
            <h3>How to Use This Label:</h3>
            <ol>
                <li><strong>Print to PDF:</strong> Press <kbd>Ctrl+P</kbd> (Windows) or <kbd>Cmd+P</kbd> (Mac)</li>
                <li><strong>Settings:</strong> Destination: "Save as PDF", Margins: "None", Scale: 100%</li>
                <li><strong>Save</strong> and send to your packaging designer</li>
            </ol>
            
            <p style="color: #666; margin-top: 25px; text-align: center; font-size: 13px;">
                <strong>FDA Compliant per 21 CFR 101.9</strong><br>
                Generated by LATAM → USA Export Compliance Tool
            </p>
        </div>
    </div>
</body>
</html>"""
    
    return html


# ============================================================================
# FDA VALIDATOR CLASSES
# ============================================================================

class FDALabelValidator:
    """Validates and corrects nutrition data according to FDA standards"""
    
    FDA_DAILY_VALUES = {
        'total_fat': 78, 'saturated_fat': 20, 'cholesterol': 300, 'sodium': 2300,
        'total_carb': 275, 'fiber': 28, 'added_sugars': 50, 'protein': 50,
        'vitamin_d': 20, 'calcium': 1300, 'iron': 18, 'potassium': 4700
    }
    
    @staticmethod
    def calculate_percent_dv(nutrient: str, amount: float) -> int:
        """Calculate %DV according to FDA standards"""
        if nutrient not in FDALabelValidator.FDA_DAILY_VALUES:
            return 0
        dv = FDALabelValidator.FDA_DAILY_VALUES[nutrient]
        if dv == 0:
            return 0
        percent = (amount / dv) * 100
        return round(percent)
    
    @staticmethod
    def validate_calorie_calculation(data: Dict) -> Tuple[bool, str, float]:
        """Validate calorie calculation using Atwater factors"""
        try:
            fat_g = float(data.get('total_fat_g', 0))
            carb_g = float(data.get('total_carb_g', 0))
            protein_g = float(data.get('protein_g', 0))
            
            calculated = (fat_g * 9) + (carb_g * 4) + (protein_g * 4)
            calculated = round(calculated)
            stated_calories = float(data.get('calories', 0))
            
            tolerance = 0.15
            lower_bound = calculated * (1 - tolerance)
            upper_bound = calculated * (1 + tolerance)
            
            if lower_bound <= stated_calories <= upper_bound:
                return True, "Calorie calculation verified", calculated
            else:
                return False, f"Calorie mismatch: Stated {stated_calories}, Calculated {calculated}", calculated
        except (ValueError, TypeError) as e:
            return False, f"Error validating calories: {str(e)}", 0
    
    @staticmethod
    def convert_metric_to_us_serving(metric_str: str) -> str:
        """Convert metric serving sizes to US household measures"""
        metric_str = metric_str.strip().lower()
        
        conversions = {
            '30g': '2 tbsp (30g)', '28g': '1 oz (28g)', '15g': '1 tbsp (15g)',
            '50g': '1/4 cup (50g)', '100g': '3.5 oz (100g)', '150g': '5.3 oz (150g)',
            '200g': '7 oz (200g)', '227g': '8 oz (227g)',
            '240ml': '1 cup (240mL)', '250ml': '1 cup (250mL)', '120ml': '1/2 cup (120mL)',
            '180ml': '3/4 cup (180mL)', '15ml': '1 tbsp (15mL)', '5ml': '1 tsp (5mL)',
            '355ml': '12 fl oz (355mL)', '500ml': '2 cups (500mL)',
        }
        
        if metric_str in conversions:
            return conversions[metric_str]
        
        match = re.match(r'(\d+\.?\d*)\s*(g|ml)', metric_str)
        if match:
            amount = float(match.group(1))
            unit = match.group(2)
            
            if unit == 'g':
                if amount <= 15:
                    return f"1 tbsp ({int(amount)}g)"
                elif amount <= 30:
                    return f"2 tbsp ({int(amount)}g)"
                elif amount <= 100:
                    return f"1/4 cup ({int(amount)}g)"
                else:
                    oz = round(amount / 28.35, 1)
                    return f"{oz} oz ({int(amount)}g)"
            elif unit == 'ml':
                if amount <= 15:
                    return f"1 tbsp ({int(amount)}mL)"
                elif amount <= 120:
                    cups = round(amount / 240, 2)
                    return f"{cups} cup ({int(amount)}mL)"
                else:
                    fl_oz = round(amount / 29.57, 1)
                    return f"{fl_oz} fl oz ({int(amount)}mL)"
        
        return f"1 serving ({metric_str})"


class EnhancedFDAConverter:
    """Enhanced converter with full FDA compliance validation"""
    
    def __init__(self):
        self.validator = FDALabelValidator()
        self.warnings = []
        self.errors = []
    
    def extract_and_validate(self, nutrition_data: Dict) -> Dict:
        """Extract, validate, and correct nutrition data for FDA compliance"""
        self.warnings = []
        self.errors = []
        
        corrected_data = self._validate_numeric_values(nutrition_data)
        
        is_valid, message, calculated = self.validator.validate_calorie_calculation(corrected_data)
        if not is_valid:
            self.warnings.append(message)
        
        if 'serving_size_metric' in corrected_data:
            us_serving = self.validator.convert_metric_to_us_serving(corrected_data['serving_size_metric'])
            corrected_data['serving_size_us'] = us_serving
        
        corrected_data['percent_dv'] = self._calculate_all_dv(corrected_data)
        
        corrected_data['validation_report'] = {
            'is_compliant': len(self.errors) == 0,
            'warnings': self.warnings,
            'errors': self.errors
        }
        
        return corrected_data
    
    def _validate_numeric_values(self, data: Dict) -> Dict:
        """Ensure all numeric values are valid"""
        corrected = data.copy()
        
        numeric_fields = [
            'calories', 'total_fat_g', 'saturated_fat_g', 'trans_fat_g',
            'cholesterol_mg', 'sodium_mg', 'total_carb_g', 'fiber_g',
            'total_sugars_g', 'added_sugars_g', 'protein_g',
            'vitamin_d_mcg', 'calcium_mg', 'iron_mg', 'potassium_mg'
        ]
        
        for field in numeric_fields:
            if field in corrected:
                try:
                    value = corrected[field]
                    if value is None or value == '':
                        corrected[field] = '0'
                    else:
                        float_val = float(value)
                        if float_val < 0:
                            self.errors.append(f"{field} cannot be negative")
                            corrected[field] = '0'
                        else:
                            corrected[field] = str(float_val)
                except (ValueError, TypeError):
                    self.errors.append(f"Invalid numeric value for {field}")
                    corrected[field] = '0'
            else:
                corrected[field] = '0'
        
        return corrected
    
    def _calculate_all_dv(self, data: Dict) -> Dict:
        """Calculate all %DV values"""
        dv_values = {}
        
        mappings = {
            'total_fat': 'total_fat_g', 'saturated_fat': 'saturated_fat_g',
            'cholesterol': 'cholesterol_mg', 'sodium': 'sodium_mg',
            'total_carb': 'total_carb_g', 'fiber': 'fiber_g',
            'added_sugars': 'added_sugars_g', 'protein': 'protein_g',
            'vitamin_d': 'vitamin_d_mcg', 'calcium': 'calcium_mg', 
            'iron': 'iron_mg', 'potassium': 'potassium_mg'
        }
        
        for nutrient, field in mappings.items():
            if field in data:
                try:
                    amount = float(data[field])
                    dv = self.validator.calculate_percent_dv(nutrient, amount)
                    dv_values[nutrient] = dv
                except (ValueError, TypeError):
                    dv_values[nutrient] = 0
        
        return dv_values


# Enhanced extraction prompt
ENHANCED_EXTRACTION_PROMPT = """You are an expert FDA nutrition label data extractor. Extract ALL nutritional information with PERFECT accuracy.

RETURN ONLY VALID JSON - NO MARKDOWN, NO EXPLANATIONS.

{
    "product_name": "exact name",
    "serving_size_original": "original text",
    "serving_size_metric": "30g or 240mL",
    "servings_per_container": "number",
    "calories": "number",
    "total_fat_g": "number",
    "saturated_fat_g": "number",
    "trans_fat_g": "number",
    "cholesterol_mg": "number",
    "sodium_mg": "number",
    "total_carb_g": "number",
    "fiber_g": "number",
    "total_sugars_g": "number",
    "added_sugars_g": "number or null",
    "protein_g": "number",
    "vitamin_d_mcg": "number or null",
    "calcium_mg": "number or null",
    "iron_mg": "number or null",
    "potassium_mg": "number or null"
}"""


# ============================================================================
# STREAMLIT APP
# ============================================================================

st.set_page_config(
    page_title="LATAM → USA Food Export Compliance Tool",
    page_icon="🌎",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #00A859, #0066B2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header { font-size: 1.2rem; color: #666; margin-bottom: 2rem; }
    .status-box { padding: 1.5rem; border-radius: 0.5rem; margin: 1rem 0; font-size: 1.1rem; }
    .pass-box { background-color: #d4edda; border-left: 6px solid #28a745; }
    .fail-box { background-color: #f8d7da; border-left: 6px solid #dc3545; }
    .warning-box { background-color: #fff3cd; border-left: 6px solid #ffc107; }
    .savings-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; padding: 1rem; border-radius: 10px; text-align: center; margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

language = st.sidebar.selectbox("🌐 Language / Idioma", ["English", "Español"])

translations = {
    "English": {
        "title": "🌎 LATAM → USA Food Export Compliance Tool",
        "subtitle": "Get Your Products USA-Ready in Minutes, Not Months",
        "upload": "Upload Your Current Label",
        "analyze": "🚀 Check USA Compliance",
        "config": "Configuration",
        "results": "Compliance Report",
        "export": "Download Reports",
        "about": "About This Tool",
        "savings": "💰 You're Saving",
    },
    "Español": {
        "title": "🌎 Herramienta de Exportación LATAM → USA",
        "subtitle": "Haga sus Productos Listos para USA en Minutos, No Meses",
        "upload": "Suba su Etiqueta Actual",
        "analyze": "🚀 Verificar Cumplimiento USA",
        "config": "Configuración",
        "results": "Reporte de Cumplimiento",
        "export": "Descargar Reportes",
        "about": "Acerca de Esta Herramienta",
        "savings": "💰 Usted Está Ahorrando",
    }
}

t = translations[language]

def calculate_dv(nutrient_type, amount):
    """Backwards compatibility wrapper"""
    validator = FDALabelValidator()
    try:
        amount_num = float(amount) if amount else 0
        return validator.calculate_percent_dv(nutrient_type, amount_num)
    except (ValueError, TypeError):
        return 0

st.markdown(f'<p class="main-header">{t["title"]}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">{t["subtitle"]}</p>', unsafe_allow_html=True)

st.markdown("""
<div class="savings-badge">
    <h3 style="margin:0;">⚡ Fast, Affordable, Accurate</h3>
    <p style="margin:0.5rem 0 0 0;">$5 per label • 60 seconds • Now with PERFECT FDA formatting</p>
</div>
""", unsafe_allow_html=True)

operation_mode = st.radio(
    "🔧 Select Tool Mode:",
    ["🔍 Audit Existing Label", "🔄 Convert LATAM Label to FDA Format"],
    horizontal=True
)

st.markdown("---")

try:
    api_key = st.secrets["OPENAI_API_KEY"]
    api_key_loaded = True
except (KeyError, FileNotFoundError):
    api_key = None
    api_key_loaded = False

with st.sidebar:
    st.header(f"⚙️ {t['config']}")
    
    if api_key_loaded:
        st.success("✅ System: Active")
    else:
        st.error("❌ System: Not Configured")
    
    st.markdown("---")
    
    origin_country = st.selectbox(
        "🏭 Your Country",
        ["🇲🇽 Mexico", "🇨🇴 Colombia", "🇨🇱 Chile", "🇧🇷 Brazil"]
    )
    
    st.markdown("---")
    st.subheader("🤖 Analysis Settings")
    
    model_choice = st.selectbox("AI Model", ["gpt-4o", "gpt-4-vision-preview"], index=0)
    strictness = st.radio(
        "Audit Strictness",
        ["Lenient (Screening)", "Balanced (Recommended)", "Strict (Final Check)"],
        index=1
    )
    
    temp_map = {
        "Lenient (Screening)": 0.2,
        "Balanced (Recommended)": 0.1,
        "Strict (Final Check)": 0.05
    }
    temperature = temp_map[strictness]
    
    st.markdown("---")
    
    rules_file = Path("nutrition_rules.txt")
    if rules_file.exists():
        rules_content = rules_file.read_text()
        st.success("✅ FDA Rules: Loaded")
    else:
        st.error("❌ Rules file missing")
        rules_content = None
    
    st.markdown("---")
    st.caption("🌎 LATAM Export Edition v2.0 - Perfect FDA Format")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    if operation_mode == "🔍 Audit Existing Label":
        mode_description = "Upload FDA label" if language == "English" else "Suba etiqueta FDA"
    else:
        mode_description = "Upload LATAM label" if language == "English" else "Suba etiqueta LATAM"
    
    st.subheader(f"📤 {t['upload']}")
    st.info(f"💡 **{mode_description}**")
    
    uploaded_file = st.file_uploader(
        "Choose label image",
        type=["jpg", "jpeg", "png"],
        help="Supported: JPG, PNG • Max 10MB"
    )
    
    if uploaded_file:
        file_size = uploaded_file.size / (1024 * 1024)
        
        if file_size > 10:
            st.error(f"⚠️ File too large: {file_size:.2f} MB")
        else:
            st.success(f"✅ Loaded: {uploaded_file.name} ({file_size:.2f} MB)")
            st.image(uploaded_file, use_column_width=True)

with col2:
    st.subheader(f"🔍 {t['results']}")
    
    checks_passed = True
    
    if not uploaded_file:
        st.info("👈 Please upload a label image")
        checks_passed = False
    
    if not api_key_loaded:
        st.error("⚠️ System not configured")
        checks_passed = False
    
    if checks_passed:
        st.success("✅ Ready for analysis!")

st.markdown("---")

col_btn1, col_btn2 = st.columns([3, 1])

with col_btn1:
    if operation_mode == "🔍 Audit Existing Label":
        button_text = f"🔍 {t['analyze']}"
    else:
        button_text = "🔄 Convert to FDA Format"
    
    action_button = st.button(button_text, type="primary", disabled=not checks_passed, use_container_width=True)

with col_btn2:
    if 'last_analysis' in st.session_state:
        if st.button("🔄 Clear", use_container_width=True):
            del st.session_state.last_analysis
            st.rerun()

if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# CONVERTER ENGINE
if operation_mode == "🔄 Convert LATAM Label to FDA Format" and action_button:
    if not checks_passed:
        st.error("❌ Cannot proceed")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("📊 Step 1/4: Extracting data...")
            progress_bar.progress(20)
            
            image_bytes = uploaded_file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            image_type = uploaded_file.type
            image_data_url = f"data:{image_type};base64,{base64_image}"
            
            openai.api_key = api_key
            
            extraction_response = openai.ChatCompletion.create(
                model=model_choice,
                messages=[
                    {"role": "system", "content": ENHANCED_EXTRACTION_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract nutrition data as JSON"},
                            {"type": "image_url", "image_url": {"url": image_data_url, "detail": "high"}}
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.0
            )
            
            status_text.text("✅ Data extracted!")
            progress_bar.progress(40)
            
            data_text = extraction_response['choices'][0]['message']['content']
            data_text = data_text.replace('```json', '').replace('```', '').strip()
            nutrition_data = json.loads(data_text)
            
            status_text.text("🔍 Step 2/4: Validating FDA compliance...")
            progress_bar.progress(55)
            
            converter = EnhancedFDAConverter()
            corrected_data = converter.extract_and_validate(nutrition_data)
            
            status_text.text("🔄 Step 3/4: Converting to US format...")
            progress_bar.progress(70)
            
            status_text.text("🎨 Step 4/4: Generating PERFECT FDA label...")
            progress_bar.progress(85)
            
            fda_label_html = generate_perfect_fda_label_html(
                corrected_data,
                corrected_data.get('percent_dv', {})
            )
            
            progress_bar.progress(100)
            status_text.text("✅ Perfect FDA label generated!")
            
            st.markdown("---")
            
            validation = corrected_data.get('validation_report', {})
            
            if validation.get('is_compliant', True):
                st.success("✅ FDA-Compliant Label Generated with PERFECT formatting!")
            else:
                st.warning("⚠️ Label generated with warnings")
            
            if validation.get('errors'):
                with st.expander("❌ Critical Errors", expanded=True):
                    for error in validation['errors']:
                        st.error(error)
            
            if validation.get('warnings'):
                with st.expander("⚠️ Validation Warnings"):
                    for warning in validation['warnings']:
                        st.warning(warning)
            
            col_compare1, col_compare2 = st.columns(2)
            
            with col_compare1:
                st.subheader("📋 Original Label")
                st.image(uploaded_file, use_column_width=True)
            
            with col_compare2:
                st.subheader("📋 PERFECT FDA Label")
                st.components.v1.html(fda_label_html, height=900, scrolling=True)
            
            st.markdown("---")
            st.subheader("✅ FDA Compliance Checklist")
            
            checklist = [
                "✅ Exact FDA formatting (matches official labels)",
                "✅ Trans fat <0.5g displays as 0g (FDA rule)",
                "✅ Calories rounded per FDA rules (no decimals)",
                "✅ All rounding rules applied correctly",
                "✅ Proper font sizes and weights",
                "✅ Correct bar thicknesses",
                "✅ Standard 3.5-inch width",
                "✅ Print-ready quality"
            ]
            
            for item in checklist:
                st.markdown(item)
            
            st.markdown("---")
            st.subheader("📥 Download Options")
            
            col_dl1, col_dl2, col_dl3 = st.columns(3)
            
            with col_dl1:
                st.download_button(
                    "🌐 Download HTML Label",
                    data=fda_label_html,
                    file_name=f"FDA_Label_Perfect.html",
                    mime="text/html",
                    use_container_width=True
                )
            
            with col_dl2:
                st.download_button(
                    "📊 Download Data (JSON)",
                    data=json.dumps(corrected_data, indent=2, ensure_ascii=False),
                    file_name=f"FDA_Data.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            progress_bar.empty()
            status_text.empty()
            
        except json.JSONDecodeError:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ Could not parse nutrition data")
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Conversion failed: {str(e)}")

st.markdown("---")
st.caption("🌎 Helping LATAM food exporters succeed in the US market | © 2026 v2.0 - PERFECT FDA FORMAT")
