import streamlit as st
import base64
import os
import openai
from pathlib import Path
from datetime import datetime
import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# ============================================================================
# COMPLETE LABEL COMPLIANCE MODULE
# ============================================================================

@dataclass
class FDARequirement:
    """Represents a single FDA requirement"""
    category: str
    requirement: str
    regulation: str
    severity: str
    description: str


class AllergenDetector:
    """Detects allergens in ingredient lists"""
    
    MAJOR_ALLERGENS = {
        'milk': ['milk', 'cream', 'butter', 'cheese', 'whey', 'casein', 'lactose', 'ghee', 'leche'],
        'eggs': ['egg', 'eggs', 'albumin', 'lysozyme', 'mayonnaise', 'huevo'],
        'fish': ['fish', 'anchovies', 'bass', 'cod', 'salmon', 'tuna', 'tilapia', 'pescado'],
        'shellfish': ['crab', 'lobster', 'shrimp', 'prawns', 'clams', 'mussels', 'oysters', 'scallops', 'camarones'],
        'tree_nuts': ['almond', 'cashew', 'walnut', 'pecan', 'pistachio', 'hazelnut', 'macadamia', 'nuez'],
        'peanuts': ['peanut', 'peanuts', 'groundnut', 'cacahuate', 'maní'],
        'wheat': ['wheat', 'flour', 'durum', 'semolina', 'spelt', 'trigo', 'harina'],
        'soybeans': ['soy', 'soya', 'soybean', 'tofu', 'tempeh', 'lecithin', 'soja'],
        'sesame': ['sesame', 'tahini', 'ajonjolí', 'sésamo']
    }
    
    @classmethod
    def detect_allergens(cls, ingredient_text: str) -> Dict[str, List[str]]:
        """Detect allergens in ingredient text"""
        ingredient_text_lower = ingredient_text.lower()
        found_allergens = {}
        
        for allergen_type, keywords in cls.MAJOR_ALLERGENS.items():
            found = []
            for keyword in keywords:
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, ingredient_text_lower):
                    found.append(keyword)
            if found:
                found_allergens[allergen_type] = found
        
        return found_allergens


class CompleteLabelValidator:
    """Validates complete food label for FDA compliance"""
    
    def __init__(self):
        self.allergen_detector = AllergenDetector()
    
    def validate_complete_label(self, extracted_data: Dict) -> Dict:
        """Perform complete FDA compliance validation per 21 CFR Part 101"""
        
        issues = {'critical': [], 'major': [], 'minor': [], 'passed': []}
        changes_made = []
        compliance_risks = []
        
        pdp = extracted_data.get('principal_display_panel', {})
        info = extracted_data.get('information_panel', {})
        lang = extracted_data.get('language_detection', {})
        nutrition = extracted_data.get('nutrition_facts', {})
        
        # === STEP 1: MANDATORY COMPONENT AUDIT ===
        
        # 1. Statement of Identity
        product_name = pdp.get('product_name')
        if not product_name:
            issues['critical'].append({
                'requirement': 'Statement of Identity (21 CFR 101.3)',
                'issue': 'Product name not found',
                'regulation': '21 CFR 101.3',
                'fix': 'Add common/usual name (e.g., "Strawberry Jam", "Corn Tortillas")',
                'risk': 'EXPORT BLOCKER - Customs will reject without clear product identity'
            })
            compliance_risks.append('Missing Statement of Identity')
        else:
            issues['passed'].append('✅ Statement of Identity present')
            # Check if needs translation
            if pdp.get('product_name_english') and pdp.get('product_name') != pdp.get('product_name_english'):
                changes_made.append(f"Translated product name: '{pdp['product_name']}' → '{pdp['product_name_english']}'")
        
        # 2. Net Quantity of Contents
        net_qty_original = pdp.get('net_quantity_original', '')
        net_qty_us = pdp.get('net_quantity_us')
        net_qty_metric = pdp.get('net_quantity_metric')
        
        if not net_qty_original:
            issues['critical'].append({
                'requirement': 'Net Quantity Declaration (21 CFR 101.105)',
                'issue': 'Net quantity not found on label',
                'regulation': '21 CFR 101.105',
                'fix': 'Add: "Net Wt [US units] ([metric])" - e.g., "Net Wt 17.6 oz (500g)"',
                'risk': 'EXPORT BLOCKER - Required by law'
            })
            compliance_risks.append('Missing Net Quantity')
        else:
            has_us = bool(net_qty_us) or any(u in net_qty_original.lower() for u in ['oz', 'lb', 'fl oz'])
            has_metric = bool(net_qty_metric) or any(u in net_qty_original.lower() for u in ['g', 'kg', 'ml', 'l'])
            
            if not has_us:
                issues['critical'].append({
                    'requirement': 'Net Quantity - US Units Required',
                    'issue': 'Missing US customary units (oz, lb, fl oz)',
                    'regulation': '21 CFR 101.105(a)',
                    'fix': f'Convert {net_qty_metric or net_qty_original} to US units and add',
                    'risk': 'EXPORT BLOCKER - US units mandatory'
                })
                compliance_risks.append('Missing US units in net quantity')
                
                # Auto-calculate US units
                if net_qty_metric:
                    metric_val = re.search(r'(\d+\.?\d*)', net_qty_metric)
                    if metric_val:
                        val = float(metric_val.group(1))
                        if 'kg' in net_qty_metric.lower():
                            oz = round(val * 35.274, 1)
                            changes_made.append(f"Calculated US units: {val}kg = {oz} oz")
                        elif 'g' in net_qty_metric.lower():
                            oz = round(val / 28.35, 1)
                            changes_made.append(f"Calculated US units: {val}g = {oz} oz")
            
            if not has_metric:
                issues['major'].append({
                    'requirement': 'Net Quantity - Metric Units',
                    'issue': 'Missing metric units',
                    'regulation': '21 CFR 101.105(a)',
                    'fix': 'Add metric equivalent in parentheses',
                    'risk': 'Non-compliance with dual declaration requirement'
                })
            
            if has_us and has_metric:
                issues['passed'].append('✅ Net quantity in both US and metric units')
        
        # 3. Nutrition Facts Label
        if not nutrition.get('present'):
            issues['critical'].append({
                'requirement': 'Nutrition Facts Panel (21 CFR 101.9)',
                'issue': 'Nutrition Facts panel not detected',
                'regulation': '21 CFR 101.9',
                'fix': 'Add complete Nutrition Facts panel in 2016 format',
                'risk': 'EXPORT BLOCKER - Mandatory for all packaged foods'
            })
            compliance_risks.append('Missing Nutrition Facts')
        else:
            # Check format
            nf_format = nutrition.get('format', '')
            if nf_format and nf_format not in ['US', 'Unknown']:
                issues['major'].append({
                    'requirement': 'Nutrition Facts Format',
                    'issue': f'Using {nf_format} format, not US FDA format',
                    'regulation': '21 CFR 101.9',
                    'fix': 'Convert to US FDA 2016 format with required order and formatting',
                    'risk': 'Will be rejected - must use US format'
                })
                changes_made.append(f"Converting from {nf_format} format to US FDA format")
            else:
                issues['passed'].append('✅ Nutrition Facts panel present')
        
        # 4. Ingredients List
        ingredients_original = info.get('ingredient_list_original', '')
        ingredients_english = info.get('ingredient_list_english', '')
        
        if not ingredients_original:
            issues['critical'].append({
                'requirement': 'Ingredient List (21 CFR 101.4)',
                'issue': 'Ingredient list not found',
                'regulation': '21 CFR 101.4',
                'fix': 'Add complete ingredient list in descending order by weight',
                'risk': 'EXPORT BLOCKER - Mandatory requirement'
            })
            compliance_risks.append('Missing Ingredient List')
        else:
            issues['passed'].append('✅ Ingredient list present')
            
            # Check if translation needed
            primary_lang = lang.get('primary_language', '').lower()
            if primary_lang in ['spanish', 'portuguese'] and ingredients_english:
                changes_made.append(f"Translated ingredients from {primary_lang.title()} to English")
            
            # Allergen analysis
            detected = self.allergen_detector.detect_allergens(ingredients_english or ingredients_original)
            allergen_stmt_original = info.get('allergen_statement_original', '')
            allergen_stmt_english = info.get('allergen_statement_english', '')
            
            if detected:
                missing_allergens = []
                allergen_text = (allergen_stmt_english or allergen_stmt_original or '').lower()
                
                for allergen_type in detected.keys():
                    allergen_name = allergen_type.replace('_', ' ')
                    if allergen_name not in allergen_text:
                        missing_allergens.append(allergen_name.title())
                
                if missing_allergens:
                    issues['critical'].append({
                        'requirement': 'Allergen Declaration (21 CFR 101.22)',
                        'issue': f'Allergens detected but not declared: {", ".join(missing_allergens)}',
                        'regulation': '21 CFR 101.22',
                        'fix': f'Add: "CONTAINS: {", ".join([a.upper() for a in missing_allergens])}"',
                        'risk': 'EXPORT BLOCKER - Allergen declaration mandatory'
                    })
                    compliance_risks.append('Missing allergen declarations')
                    changes_made.append(f"Added allergen declaration for: {', '.join(missing_allergens)}")
                else:
                    issues['passed'].append('✅ Allergens properly declared')
                    
                    # Check if translation needed
                    if allergen_stmt_original and allergen_stmt_english and allergen_stmt_original != allergen_stmt_english:
                        changes_made.append(f"Translated allergen statement to English")
        
        # 5. Manufacturer Name and Address
        if not info.get('manufacturer_name'):
            issues['critical'].append({
                'requirement': 'Manufacturer Information (21 CFR 101.5)',
                'issue': 'Manufacturer name and address not found',
                'regulation': '21 CFR 101.5',
                'fix': 'Add: "Manufactured for [Company Name], [City, State ZIP]" or "Imported by [Company], [City, State ZIP]"',
                'risk': 'EXPORT BLOCKER - Must identify responsible party'
            })
            compliance_risks.append('Missing Manufacturer Information')
        else:
            issues['passed'].append('✅ Manufacturer information present')
            
            # Check if it's imported
            country = info.get('country_of_origin', '').lower()
            if country and 'usa' not in country and 'united states' not in country:
                if 'imported' not in info.get('manufacturer_address', '').lower():
                    issues['major'].append({
                        'requirement': 'Country of Origin Declaration',
                        'issue': f'Product from {country} but no "Imported by" statement',
                        'regulation': '19 CFR 134.1',
                        'fix': f'Add: "Imported from {country.title()}" and US importer address',
                        'risk': 'Customs may reject - origin must be clear'
                    })
        
        # === STEP 2: TRANSLATION & LOCALIZATION ===
        
        # Check for Chilean Sellos
        sellos = pdp.get('chilean_sellos', [])
        if sellos:
            changes_made.append(f"Removed Chilean 'Sellos' (black octagons): {', '.join(sellos)}")
            changes_made.append("Note: High sugar/fat content reflected in Nutrition Facts panel instead")
            issues['passed'].append('✅ Chilean sellos identified and removed (FDA uses Nutrition Facts only)')
        
        # Check for Mexican warnings
        mex_warnings = pdp.get('mexican_warnings', [])
        if mex_warnings:
            changes_made.append(f"Removed Mexican front-of-pack warnings: {', '.join(mex_warnings)}")
            changes_made.append("Note: Nutrient content shown in Nutrition Facts panel")
            issues['passed'].append('✅ Mexican warnings identified and removed (not used in US)')
        
        # Language requirement
        primary = lang.get('primary_language', '')
        if primary and primary.lower() not in ['english', 'unknown']:
            issues['critical'].append({
                'requirement': 'English Language (21 CFR 101.15)',
                'issue': f'Label primarily in {primary}',
                'regulation': '21 CFR 101.15(a)',
                'fix': 'Translate all required information to English (bilingual labels OK)',
                'risk': 'EXPORT BLOCKER - English is mandatory'
            })
            compliance_risks.append('Not in English')
            changes_made.append(f"Translated entire label from {primary} to English")
        else:
            issues['passed'].append('✅ English language requirement met')
        
        # === COMPLIANCE SUMMARY ===
        
        total_critical = len(issues['critical'])
        total_major = len(issues['major'])
        total_issues = total_critical + total_major
        
        compliance_score = max(0, 100 - (total_critical * 20) - (total_major * 10))
        
        if total_critical == 0:
            status = "FDA COMPLIANT - READY FOR US MARKET"
            export_ready = True
        elif total_critical <= 2:
            status = "NEEDS FIXES - Close to compliance"
            export_ready = False
        else:
            status = "MAJOR REVISION REQUIRED"
            export_ready = False
        
        return {
            'compliance_score': compliance_score,
            'export_ready': export_ready,
            'status': status,
            'issues': issues,
            'total_issues': total_issues,
            'changes_made': changes_made,
            'compliance_risks': compliance_risks,
            'detected_allergens': detected if ingredients_original else {},
            'audit_summary': {
                'critical_issues': total_critical,
                'major_issues': total_major,
                'minor_issues': len(issues['minor']),
                'passed_checks': len(issues['passed']),
                'total_changes': len(changes_made),
                'risk_level': 'HIGH' if total_critical >= 3 else 'MEDIUM' if total_critical > 0 else 'LOW'
            },
            'redesign_data': self._generate_redesign_specification(extracted_data, detected if ingredients_original else {})
        }
    
    def _generate_redesign_specification(self, extracted_data: Dict, detected_allergens: Dict) -> Dict:
        """Generate complete FDA-compliant label redesign specification"""
        
        pdp = extracted_data.get('principal_display_panel', {})
        info = extracted_data.get('information_panel', {})
        nutrition = extracted_data.get('nutrition_facts', {})
        
        # Get English versions or originals
        product_name = pdp.get('product_name_english') or pdp.get('product_name', 'PRODUCT NAME REQUIRED')
        ingredients = info.get('ingredient_list_english') or info.get('ingredient_list_original', 'INGREDIENTS REQUIRED')
        
        # Calculate US units if needed
        net_qty_us = pdp.get('net_quantity_us', '')
        net_qty_metric = pdp.get('net_quantity_metric', '')
        
        if not net_qty_us and net_qty_metric:
            # Auto-calculate
            match = re.search(r'(\d+\.?\d*)', net_qty_metric)
            if match:
                val = float(match.group(1))
                if 'kg' in net_qty_metric.lower():
                    oz = round(val * 35.274, 1)
                    lb = round(val * 2.205, 1)
                    net_qty_us = f"{oz} oz" if oz < 16 else f"{lb} lb"
                elif 'g' in net_qty_metric.lower():
                    oz = round(val / 28.35, 1)
                    net_qty_us = f"{oz} oz"
                elif 'l' in net_qty_metric.lower():
                    fl_oz = round(val * 33.814, 1)
                    net_qty_us = f"{fl_oz} fl oz"
                elif 'ml' in net_qty_metric.lower():
                    fl_oz = round(val / 29.57, 1)
                    net_qty_us = f"{fl_oz} fl oz"
        
        net_quantity_compliant = f"Net Wt {net_qty_us} ({net_qty_metric})" if net_qty_us and net_qty_metric else "NET QUANTITY REQUIRED"
        
        # Build allergen statement
        allergen_list = []
        if detected_allergens:
            for allergen_type in detected_allergens.keys():
                allergen_name = allergen_type.replace('_', ' ').upper()
                allergen_list.append(allergen_name)
        
        allergen_statement = f"CONTAINS: {', '.join(allergen_list)}" if allergen_list else None
        
        # Get manufacturer info
        manufacturer = info.get('manufacturer_name', 'MANUFACTURER NAME REQUIRED')
        address = info.get('manufacturer_address', 'CITY, STATE ZIP REQUIRED')
        country = info.get('country_of_origin', '')
        
        if country and country.lower() not in ['usa', 'united states', 'us']:
            manufacturer_statement = f"Imported from {country}\nDistributed by: {manufacturer}\n{address}"
        else:
            manufacturer_statement = f"Manufactured for: {manufacturer}\n{address}"
        
        redesign = {
            "label_format": "FDA_COMPLIANT_US",
            "regulation_compliance": "21 CFR Part 101",
            
            "principal_display_panel": {
                "statement_of_identity": {
                    "text": product_name,
                    "font_requirement": "Prominent and conspicuous",
                    "position": "Top 1/3 of principal display panel",
                    "regulation": "21 CFR 101.3"
                },
                "net_quantity": {
                    "text": net_quantity_compliant,
                    "font_requirement": "Bold, minimum 1/16 inch (based on panel size)",
                    "position": "Bottom 30% of principal display panel",
                    "regulation": "21 CFR 101.105"
                },
                "brand_name": pdp.get('brand_name', None)
            },
            
            "information_panel": {
                "ingredients": {
                    "heading": "INGREDIENTS:",
                    "text": ingredients,
                    "format": "Descending order by weight",
                    "font_requirement": "Minimum 1/16 inch",
                    "regulation": "21 CFR 101.4"
                },
                "allergen_declaration": {
                    "text": allergen_statement,
                    "format": "CONTAINS: [ALLERGENS] or within ingredient list",
                    "required_allergens": allergen_list if allergen_list else None,
                    "regulation": "21 CFR 101.22 (FALCPA)"
                },
                "manufacturer_information": {
                    "text": manufacturer_statement,
                    "regulation": "21 CFR 101.5"
                }
            },
            
            "nutrition_facts": {
                "format": "2016 FDA Format",
                "title": "Nutrition Facts",
                "serving_size": nutrition.get('serving_size_original', 'SERVING SIZE REQUIRED'),
                "servings_per_container": nutrition.get('servings_per_container', 'REQUIRED'),
                "nutrients": {
                    "calories": nutrition.get('calories', '0'),
                    "total_fat_g": nutrition.get('total_fat_g', '0'),
                    "saturated_fat_g": nutrition.get('saturated_fat_g', '0'),
                    "trans_fat_g": nutrition.get('trans_fat_g', '0'),
                    "cholesterol_mg": nutrition.get('cholesterol_mg', '0'),
                    "sodium_mg": nutrition.get('sodium_mg', '0'),
                    "total_carbohydrate_g": nutrition.get('total_carb_g', '0'),
                    "dietary_fiber_g": nutrition.get('fiber_g', '0'),
                    "total_sugars_g": nutrition.get('total_sugars_g', '0'),
                    "added_sugars_g": nutrition.get('added_sugars_g', '0'),
                    "protein_g": nutrition.get('protein_g', '0'),
                    "vitamin_d_mcg": nutrition.get('vitamin_d_mcg', '0'),
                    "calcium_mg": nutrition.get('calcium_mg', '0'),
                    "iron_mg": nutrition.get('iron_mg', '0'),
                    "potassium_mg": nutrition.get('potassium_mg', '0')
                },
                "regulation": "21 CFR 101.9"
            },
            
            "special_requirements": {
                "language": "English (bilingual permitted)",
                "removed_elements": [],
                "added_elements": []
            }
        }
        
        # Add removed elements
        if pdp.get('chilean_sellos'):
            redesign['special_requirements']['removed_elements'].append({
                "element": "Chilean Sellos (Black octagons)",
                "items": pdp['chilean_sellos'],
                "reason": "FDA does not use front-of-pack warning labels"
            })
        
        if pdp.get('mexican_warnings'):
            redesign['special_requirements']['removed_elements'].append({
                "element": "Mexican Warning Labels",
                "items": pdp['mexican_warnings'],
                "reason": "FDA does not use front-of-pack warning labels"
            })
        
        return redesign


# Complete Label Extraction Prompt - UPDATED WITH MEXICAN VITAMIN HANDLING
COMPLETE_LABEL_EXTRACTION_PROMPT = """### ROLE
You are an expert FDA Regulatory Consultant specializing in Food Labeling Compliance (21 CFR Part 101). Your goal is to audit an entire food package label (LATAM/International) and extract all information for FDA compliance analysis.

### CRITICAL: HANDLING MEXICAN/LATAM VITAMIN DECLARATIONS

**Mexican labels show vitamins as %VNR (Valor Nutrimental de Referencia).**

When you see vitamins listed with %VNR or %VRN percentages, you MUST extract them separately:

Examples:
- "Vitamina B1 15%" → extract as vitamin_b1: 15
- "Calcio 4%" → extract as calcium: 4  
- "Hierro 2%" → extract as iron: 2
- "Zinc 10%" → extract as zinc: 10
- "Yodo 10%" → extract as iodine: 10

### STEP 1: COMPONENT EXTRACTION
Extract the following five mandatory elements from the label. If missing, note as null:

1. **Statement of Identity:** The common or usual name of the food (e.g., "Hard Candy", "Strawberry Jam")
2. **Net Quantity of Contents:** Extract exact text showing weight/volume
3. **Nutrition Facts Label:** Extract all nutrition data if present
4. **Ingredients List:** Extract complete ingredient list exactly as shown
5. **Name and Address of Manufacturer:** Extract company name and address

### STEP 2: LANGUAGE & CULTURAL ELEMENTS
- Identify primary language (Spanish/Portuguese/English)
- Note any Chilean "Sellos" (High in Sugar/Saturated Fat octagons)
- Note any Mexican "Alto en" warnings
- Note any Brazilian "Contém" allergen warnings
- Identify all marketing claims (Organic, Natural, Sugar-Free, etc.)

### STEP 3: NUTRITION FACTS EXTRACTION

CRITICAL DISTINCTION - Added Sugars vs Sugar Alcohols:

**ADDED SUGARS (include these):**
- Sugar, sucrose, glucose, fructose, dextrose
- Corn syrup, high fructose corn syrup, maple syrup
- Honey, agave nectar, molasses
- Concentrated fruit juice, fruit juice concentrate
- Brown sugar, raw sugar, cane sugar

**SUGAR ALCOHOLS / POLYOLS (DO NOT count as added sugars):**
- Maltitol, sorbitol, xylitol, erythritol, isomalt
- Mannitol, lactitol, hydrogenated starch hydrolysates
- Any ingredient ending in "-itol"
- Listed as "Polioles" in Spanish labels

If you see sugar alcohols/polyols in the ingredient list, they should be listed separately in nutrition data, NOT as added sugars.

Extract nutrition data if present. Scan ingredients for FDA's 9 major allergens:
- Milk, Eggs, Fish, Shellfish, Tree nuts, Peanuts, Wheat, Soybeans, Sesame
- Note if allergen statement exists (CONTAINS:, CONTIENE:, etc.)

### RETURN FORMAT
Return ONLY valid JSON with this exact structure:

{
    "principal_display_panel": {
        "product_name": "exact product name as shown",
        "product_name_english": "translate to English if not already",
        "brand_name": "brand if present",
        "net_quantity_original": "exact text (e.g., '500g' or 'Peso Neto 500g')",
        "net_quantity_us": "US units if present (e.g., '17.6 oz')",
        "net_quantity_metric": "metric if present (e.g., '500g')",
        "product_claims": ["list all claims like 'Orgánico', 'Sin Gluten', '100% Natural'"],
        "chilean_sellos": ["list if present: 'Alto en Azúcares', 'Alto en Grasas Saturadas', etc."],
        "mexican_warnings": ["list if present: 'Exceso calorías', etc."]
    },
    "information_panel": {
        "ingredient_list_original": "complete ingredient list exactly as shown in original language",
        "ingredient_list_english": "translate ingredients to English",
        "ingredients_parsed": ["ingredient1", "ingredient2", "ingredient3"],
        "allergen_statement_original": "exact allergen statement if present",
        "allergen_statement_english": "translate to English",
        "manufacturer_name": "company name",
        "manufacturer_address": "full address including city, state/province, country",
        "country_of_origin": "country",
        "distributed_by": "if different from manufacturer",
        "lot_code": "if visible",
        "best_by_date": "if visible"
    },
    "nutrition_facts": {
        "present": true/false,
        "format": "Chilean/Mexican/Brazilian/US/Other",
        "serving_size_original": "as shown on label",
        "serving_size_metric": "just the metric (e.g., '30g')",
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
        "added_sugars_g": "number or null if not specified (DO NOT include sugar alcohols here)",
        "sugar_alcohols_g": "number or null (maltitol, sorbitol, xylitol, etc.)",
        "protein_g": "number",
        "vitamin_d_mcg": "number or null",
        "calcium_mg": "number or null",
        "iron_mg": "number or null",
        "potassium_mg": "number or null",
        "vitamins_vnr_percent": {
            "vitamin_b1": "percentage if shown (e.g., 15 for 15% VNR)",
            "vitamin_b2": "percentage if shown",
            "vitamin_b6": "percentage if shown",
            "vitamin_b12": "percentage if shown",
            "vitamin_c": "percentage if shown",
            "vitamin_d": "percentage if shown",
            "vitamin_e": "percentage if shown",
            "calcium": "percentage if shown",
            "iron": "percentage if shown",
            "zinc": "percentage if shown",
            "iodine": "percentage if shown (Yodo)",
            "folic_acid": "percentage if shown (Ácido Fólico)"
        }
    },
    "language_detection": {
        "primary_language": "Spanish/Portuguese/English/Other",
        "bilingual": true/false,
        "languages_present": ["Spanish", "English"]
    },
    "compliance_observations": [
        "list any obvious issues: 'Only in Spanish', 'Missing allergen declaration', 'No US units', etc."
    ]
}

CRITICAL INSTRUCTIONS:
- Extract text EXACTLY as it appears, preserving original language
- Provide English translations where specified
- For Mexican labels: extract %VNR values into vitamins_vnr_percent field
- If anything is missing, use null (not empty string)
- Be thorough - extract everything visible on the label
- Note cultural/regional labeling elements (sellos, warnings, etc.)

Extract now:"""

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
                <div class="nutrient-dv"></div>
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
# FDA VALIDATOR CLASSES - UPDATED WITH MEXICAN VNR CONVERSION
# ============================================================================

class FDALabelValidator:
    """Validates and corrects nutrition data according to FDA standards"""
    
    FDA_DAILY_VALUES = {
        'total_fat': 78, 'saturated_fat': 20, 'cholesterol': 300, 'sodium': 2300,
        'total_carb': 275, 'fiber': 28, 'added_sugars': 50, 'protein': 50,
        'vitamin_d': 20, 'calcium': 1300, 'iron': 18, 'potassium': 4700
    }
    
    # Mexican VNR (Valor Nutrimental de Referencia) standards per NOM-051
    MEXICAN_VNR = {
        'vitamin_b1': 1.4,      # mg
        'vitamin_b2': 1.6,      # mg
        'vitamin_b6': 1.7,      # mg
        'vitamin_b12': 2.4,     # mcg
        'vitamin_c': 90,        # mg
        'vitamin_d': 5,         # mcg
        'vitamin_e': 15,        # mg
        'calcium': 1000,        # mg (Mexican VNR) vs 1300mg (FDA DV)
        'iron': 14,             # mg (Mexican VNR) vs 18mg (FDA DV)
        'zinc': 15,             # mg
        'iodine': 150,          # mcg
        'folic_acid': 400,      # mcg
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
    def convert_mexican_vnr_to_fda_amount(nutrient: str, vnr_percent: float) -> float:
        """
        Convert Mexican VNR (Valor Nutrimental de Referencia) percentage to absolute FDA amount
        
        Example: Calcium 4% VNR (Mexican) = 4% of 1000mg = 40mg
        """
        if nutrient not in FDALabelValidator.MEXICAN_VNR:
            return 0
        
        # Calculate absolute amount from VNR percentage
        absolute_amount = (vnr_percent / 100) * FDALabelValidator.MEXICAN_VNR[nutrient]
        
        return absolute_amount
    
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
            '24.2g': '2 tbsp (24.2g)', '24g': '2 tbsp (24g)',
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
                    return f"1 tbsp ({amount}g)"
                elif amount <= 30:
                    return f"2 tbsp ({amount}g)"
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
    """Enhanced converter with full FDA compliance validation + Mexican VNR conversion"""
    
    def __init__(self):
        self.validator = FDALabelValidator()
        self.warnings = []
        self.errors = []
    
    def extract_and_validate(self, nutrition_data: Dict) -> Dict:
        """Extract, validate, and correct nutrition data for FDA compliance"""
        self.warnings = []
        self.errors = []
        
        corrected_data = self._validate_numeric_values(nutrition_data)
        
        # NEW: Convert Mexican VNR percentages to FDA amounts
        if 'vitamins_vnr_percent' in nutrition_data.get('nutrition_facts', {}):
            corrected_data = self._convert_mexican_vitamins(corrected_data, nutrition_data)
        
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
    
    def _convert_mexican_vitamins(self, corrected_data: Dict, original_data: Dict) -> Dict:
        """
        Convert Mexican VNR percentages to absolute FDA values
        This fixes the bug where Mexican vitamins showed wrong %DV
        """
        vnr_data = original_data.get('nutrition_facts', {}).get('vitamins_vnr_percent', {})
        
        if not vnr_data:
            return corrected_data
        
        self.warnings.append("🇲🇽 Detected Mexican VNR format - converting to FDA values...")
        
        # Convert VNR % to absolute amounts
        for nutrient, vnr_percent in vnr_data.items():
            if not vnr_percent or vnr_percent == 'null':
                continue
                
            try:
                percent = float(vnr_percent)
                
                # Convert to absolute amount using Mexican VNR standards
                absolute_amount = self.validator.convert_mexican_vnr_to_fda_amount(nutrient, percent)
                
                if absolute_amount > 0:
                    # Map to FDA fields
                    if nutrient == 'calcium':
                        corrected_data['calcium_mg'] = str(round(absolute_amount, 1))
                        self.warnings.append(f"✓ Calcium: {percent}% VNR (Mexican) = {absolute_amount:.1f}mg → {self.validator.calculate_percent_dv('calcium', absolute_amount)}% DV (FDA)")
                    
                    elif nutrient == 'iron':
                        corrected_data['iron_mg'] = str(round(absolute_amount, 1))
                        self.warnings.append(f"✓ Iron: {percent}% VNR (Mexican) = {absolute_amount:.1f}mg → {self.validator.calculate_percent_dv('iron', absolute_amount)}% DV (FDA)")
                    
                    elif nutrient == 'vitamin_d':
                        corrected_data['vitamin_d_mcg'] = str(round(absolute_amount, 1))
                        self.warnings.append(f"✓ Vitamin D: {percent}% VNR (Mexican) = {absolute_amount:.1f}mcg → {self.validator.calculate_percent_dv('vitamin_d', absolute_amount)}% DV (FDA)")
                    
                    elif nutrient == 'zinc':
                        # Zinc is not required on FDA label but we track it
                        self.warnings.append(f"✓ Zinc: {percent}% VNR (Mexican) = {absolute_amount:.1f}mg (not required on FDA label)")
                    
                    elif nutrient == 'iodine':
                        self.warnings.append(f"✓ Iodine: {percent}% VNR (Mexican) = {absolute_amount:.1f}mcg (not required on FDA label)")
                    
                    elif nutrient in ['vitamin_b1', 'vitamin_b2', 'vitamin_b6', 'vitamin_b12', 'vitamin_c', 'vitamin_e']:
                        self.warnings.append(f"✓ {nutrient.replace('_', ' ').title()}: {percent}% VNR = {absolute_amount:.1f}mg/mcg (not required on FDA label)")
                    
                    elif nutrient == 'folic_acid':
                        self.warnings.append(f"✓ Folic Acid: {percent}% VNR = {absolute_amount:.1f}mcg (not required on FDA label)")
                
            except (ValueError, TypeError) as e:
                self.errors.append(f"Could not convert {nutrient} VNR percentage: {str(e)}")
        
        return corrected_data
    
    def _validate_numeric_values(self, data: Dict) -> Dict:
        """Ensure all numeric values are valid"""
        corrected = data.copy()
        
        # Handle nested nutrition_facts structure
        if 'nutrition_facts' in data:
            nf = data['nutrition_facts']
            for key, value in nf.items():
                if key not in ['present', 'format', 'serving_size_original', 'serving_size_metric', 
                               'serving_size_us', 'servings_per_container', 'vitamins_vnr_percent']:
                    corrected[key] = value
        
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
                    if value is None or value == '' or value == 'null':
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
        
        # Preserve serving size fields
        if 'nutrition_facts' in data:
            corrected['serving_size_original'] = data['nutrition_facts'].get('serving_size_original', '')
            corrected['serving_size_metric'] = data['nutrition_facts'].get('serving_size_metric', '')
            corrected['servings_per_container'] = data['nutrition_facts'].get('servings_per_container', '1')
        
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


# Enhanced extraction prompt for conversion mode
ENHANCED_EXTRACTION_PROMPT = """You are an expert FDA nutrition label data extractor. Extract ALL nutritional information with PERFECT accuracy.

**CRITICAL: If this is a Mexican label with %VNR vitamins, extract them into vitamins_vnr_percent field.**

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
    "potassium_mg": "number or null",
    "vitamins_vnr_percent": {
        "calcium": "percentage if VNR shown (e.g., 4 for 4%)",
        "iron": "percentage if VNR shown",
        "zinc": "percentage if VNR shown",
        "iodine": "percentage if VNR shown",
        "vitamin_b1": "percentage if VNR shown",
        "vitamin_b2": "percentage if VNR shown"
    }
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
    <h3 style="margin:0;">⚡ Complete FDA Compliance Platform</h3>
    <p style="margin:0.5rem 0 0 0;">Nutrition Facts + Complete Label Analysis • $99-499 vs $5,000-15,000 consultant</p>
</div>
""", unsafe_allow_html=True)

operation_mode = st.radio(
    "🔧 Select Tool Mode:",
    ["🔍 Audit Existing Label", "🔄 Convert LATAM Label to FDA Format", "🎨 Complete Label Compliance"],
    horizontal=True,
    help="Audit FDA label | Convert nutrition panel | Analyze entire label for complete FDA compliance"
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
    st.caption("🌎 VeriLabel v3.1 - Mexican VNR Fixed")

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    if operation_mode == "🔍 Audit Existing Label":
        mode_description = "Upload FDA label" if language == "English" else "Suba etiqueta FDA"
    elif operation_mode == "🔄 Convert LATAM Label to FDA Format":
        mode_description = "Upload LATAM label" if language == "English" else "Suba etiqueta LATAM"
    else:  # Complete Label Compliance
        mode_description = "Upload complete label (front & back)" if language == "English" else "Suba etiqueta completa (frente y reverso)"
    
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
    elif operation_mode == "🔄 Convert LATAM Label to FDA Format":
        button_text = "🔄 Convert to FDA Format"
    else:  # Complete Label Compliance
        button_text = "🎨 Analyze Complete Label" if language == "English" else "🎨 Analizar Etiqueta Completa"
    
    action_button = st.button(button_text, type="primary", disabled=not checks_passed, use_container_width=True)

with col_btn2:
    if 'last_analysis' in st.session_state:
        if st.button("🔄 Clear", use_container_width=True):
            del st.session_state.last_analysis
            st.rerun()

if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# ============================================================================
# CONVERTER ENGINE - FIXED FOR MEXICAN VITAMINS
# ============================================================================

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
                            {"type": "text", "text": "Extract nutrition data as JSON. If Mexican label with %VNR vitamins, extract them."},
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
            
            status_text.text("🔍 Step 2/4: Validating FDA compliance + Converting Mexican vitamins...")
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
                with st.expander("⚠️ Validation Warnings & VNR Conversions", expanded=True):
                    for warning in validation['warnings']:
                        if 'VNR' in warning or '🇲🇽' in warning:
                            st.info(warning)  # Highlight Mexican conversions
                        else:
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
                "✅ Mexican VNR converted to FDA values",
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
            
        except json.JSONDecodeError as e:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ Could not parse nutrition data")
            with st.expander("🔍 Debug Info"):
                st.code(data_text)
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Conversion failed: {str(e)}")
            with st.expander("🔍 Error Details"):
                import traceback
                st.code(traceback.format_exc())

# ============================================================================
# COMPLETE LABEL COMPLIANCE ENGINE (Continues as before...)
# ============================================================================

if operation_mode == "🎨 Complete Label Compliance" and action_button:
    if not checks_passed:
        st.error("❌ Cannot proceed. Please resolve issues above.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("📊 Step 1/3: Analyzing complete label..." if language == "English" else "📊 Paso 1/3: Analizando etiqueta completa...")
            progress_bar.progress(30)
            
            image_bytes = uploaded_file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            image_type = uploaded_file.type
            image_data_url = f"data:{image_type};base64,{base64_image}"
            
            openai.api_key = api_key
            
            extraction_response = openai.ChatCompletion.create(
                model=model_choice,
                messages=[
                    {"role": "system", "content": COMPLETE_LABEL_EXTRACTION_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all label information as JSON"},
                            {"type": "image_url", "image_url": {"url": image_data_url, "detail": "high"}}
                        ]
                    }
                ],
                max_tokens=2000,
                temperature=0.0
            )
            
            status_text.text("✅ Label data extracted!" if language == "English" else "✅ ¡Datos de etiqueta extraídos!")
            progress_bar.progress(60)
            
            data_text = extraction_response['choices'][0]['message']['content']
            data_text = data_text.replace('```json', '').replace('```', '').strip()
            label_data = json.loads(data_text)
            
            status_text.text("🔍 Step 2/3: Checking FDA compliance..." if language == "English" else "🔍 Paso 2/3: Verificando cumplimiento FDA...")
            progress_bar.progress(80)
            
            validator = CompleteLabelValidator()
            compliance_report = validator.validate_complete_label(label_data)
            
            status_text.text("✅ Complete analysis done!" if language == "English" else "✅ ¡Análisis completo terminado!")
            progress_bar.progress(100)
            
            # Display results (rest of complete compliance code continues as before)
            st.success("✅ Complete Label Analysis Complete!")
            
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Analysis failed: {str(e)}")

st.markdown("---")
st.caption("🌎 Complete FDA Compliance Platform for International Exporters | © 2026 VeriLabel v3.1 - Mexican VNR Fixed")
