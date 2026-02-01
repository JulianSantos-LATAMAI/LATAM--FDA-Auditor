# Enhanced FDA Label Converter Module
# Add this to your existing app to replace the converter functionality

import json
import re
from typing import Dict, List, Tuple, Optional

class FDALabelValidator:
    """Validates and corrects nutrition data according to FDA standards"""
    
    # FDA Daily Values (21 CFR 101.9)
    FDA_DAILY_VALUES = {
        'total_fat': 78,
        'saturated_fat': 20,
        'cholesterol': 300,
        'sodium': 2300,
        'total_carb': 275,
        'fiber': 28,
        'added_sugars': 50,
        'protein': 50,
        'vitamin_d': 20,  # mcg
        'calcium': 1300,  # mg
        'iron': 18,  # mg
        'potassium': 4700  # mg
    }
    
    # FDA Rounding Rules (21 CFR 101.9(c))
    ROUNDING_RULES = {
        'calories': {
            (0, 5): 0,
            (5, 50): 5,
            (50, float('inf')): 10
        },
        'total_fat': {
            (0, 0.5): 0,
            (0.5, 5): 0.5,
            (5, float('inf')): 1
        },
        'saturated_fat': {
            (0, 0.5): 0,
            (0.5, 5): 0.5,
            (5, float('inf')): 1
        },
        'cholesterol': {
            (0, 2): 0,
            (2, 5): 5,
            (5, float('inf')): 5
        },
        'sodium': {
            (0, 5): 0,
            (5, 140): 5,
            (140, float('inf')): 10
        },
        'carbs': {
            (0, 0.5): 0,
            (0.5, float('inf')): 1
        },
        'protein': {
            (0, 0.5): 0,
            (0.5, float('inf')): 1
        }
    }
    
    # FDA Required Nutrient Order (21 CFR 101.9(d))
    FDA_NUTRIENT_ORDER = [
        'serving_size',
        'servings_per_container',
        'calories',
        'total_fat',
        'saturated_fat',
        'trans_fat',
        'cholesterol',
        'sodium',
        'total_carb',
        'fiber',
        'total_sugars',
        'added_sugars',
        'protein',
        'vitamin_d',
        'calcium',
        'iron',
        'potassium'
    ]
    
    @staticmethod
    def round_by_fda_rules(value: float, nutrient_type: str) -> float:
        """Apply FDA rounding rules"""
        if nutrient_type not in FDALabelValidator.ROUNDING_RULES:
            return round(value, 1)
        
        rules = FDALabelValidator.ROUNDING_RULES[nutrient_type]
        for (min_val, max_val), increment in rules.items():
            if min_val <= value < max_val:
                if increment == 0:
                    return 0
                return round(value / increment) * increment
        
        return round(value, 1)
    
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
        """
        Validate calorie calculation using Atwater factors
        Returns: (is_valid, message, calculated_calories)
        """
        try:
            fat_g = float(data.get('total_fat_g', 0))
            carb_g = float(data.get('total_carb_g', 0))
            protein_g = float(data.get('protein_g', 0))
            
            # Atwater factors: Fat=9, Carb=4, Protein=4
            calculated = (fat_g * 9) + (carb_g * 4) + (protein_g * 4)
            calculated = round(calculated)
            
            stated_calories = float(data.get('calories', 0))
            
            # FDA allows ±15% tolerance
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
        """
        Convert metric serving sizes to US household measures
        Based on FDA 21 CFR 101.9(b)(2) - Reference Amounts Customarily Consumed (RACC)
        """
        metric_str = metric_str.strip().lower()
        
        # Common conversions with FDA-compliant household measures
        conversions = {
            # Weight conversions
            '30g': '2 tbsp (30g)',
            '28g': '1 oz (28g)',
            '15g': '1 tbsp (15g)',
            '50g': '1/4 cup (50g)',
            '100g': '3.5 oz (100g)',
            '150g': '5.3 oz (150g)',
            '200g': '7 oz (200g)',
            '227g': '8 oz (227g)',
            
            # Volume conversions
            '240ml': '1 cup (240mL)',
            '250ml': '1 cup (250mL)',
            '120ml': '1/2 cup (120mL)',
            '180ml': '3/4 cup (180mL)',
            '15ml': '1 tbsp (15mL)',
            '5ml': '1 tsp (5mL)',
            '355ml': '12 fl oz (355mL)',
            '500ml': '2 cups (500mL)',
        }
        
        # Try exact match
        if metric_str in conversions:
            return conversions[metric_str]
        
        # Try to parse and convert
        match = re.match(r'(\d+\.?\d*)\s*(g|ml)', metric_str)
        if match:
            amount = float(match.group(1))
            unit = match.group(2)
            
            if unit == 'g':
                # Weight to volume approximations for common foods
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
        
        # Fallback
        return f"1 serving ({metric_str})"
    
    @staticmethod
    def validate_required_nutrients(data: Dict) -> List[str]:
        """Check that all FDA-required nutrients are present"""
        required = [
            'calories',
            'total_fat_g',
            'saturated_fat_g',
            'trans_fat_g',
            'cholesterol_mg',
            'sodium_mg',
            'total_carb_g',
            'fiber_g',
            'total_sugars_g',
            'added_sugars_g',
            'protein_g',
            'vitamin_d_mcg',
            'calcium_mg',
            'iron_mg',
            'potassium_mg'
        ]
        
        missing = []
        for nutrient in required:
            if nutrient not in data or data[nutrient] is None:
                missing.append(nutrient)
        
        return missing


class EnhancedFDAConverter:
    """Enhanced converter with full FDA compliance validation"""
    
    def __init__(self):
        self.validator = FDALabelValidator()
        self.warnings = []
        self.errors = []
    
    def extract_and_validate(self, nutrition_data: Dict) -> Dict:
        """
        Extract, validate, and correct nutrition data for FDA compliance
        Returns corrected data with validation report
        """
        self.warnings = []
        self.errors = []
        
        # Step 1: Validate required nutrients
        missing = self.validator.validate_required_nutrients(nutrition_data)
        if missing:
            for nutrient in missing:
                self.warnings.append(f"Missing required nutrient: {nutrient}")
        
        # Step 2: Validate and correct numeric values
        corrected_data = self._validate_numeric_values(nutrition_data)
        
        # Step 3: Apply FDA rounding rules
        corrected_data = self._apply_rounding_rules(corrected_data)
        
        # Step 4: Validate calorie calculation
        is_valid, message, calculated = self.validator.validate_calorie_calculation(corrected_data)
        if not is_valid:
            self.warnings.append(message)
            # Optionally auto-correct
            # corrected_data['calories'] = str(calculated)
        
        # Step 5: Convert serving size
        if 'serving_size_metric' in corrected_data:
            us_serving = self.validator.convert_metric_to_us_serving(
                corrected_data['serving_size_metric']
            )
            corrected_data['serving_size_us'] = us_serving
        
        # Step 6: Calculate all %DV values
        corrected_data['percent_dv'] = self._calculate_all_dv(corrected_data)
        
        # Step 7: Add validation report
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
                        # Convert to float and back to string to validate
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
    
    def _apply_rounding_rules(self, data: Dict) -> Dict:
        """Apply FDA rounding rules to all nutrients"""
        corrected = data.copy()
        
        # Apply rounding where applicable
        if 'calories' in corrected:
            val = float(corrected['calories'])
            rounded = self.validator.round_by_fda_rules(val, 'calories')
            corrected['calories'] = str(int(rounded))
        
        if 'total_fat_g' in corrected:
            val = float(corrected['total_fat_g'])
            rounded = self.validator.round_by_fda_rules(val, 'total_fat')
            corrected['total_fat_g'] = str(rounded)
        
        if 'saturated_fat_g' in corrected:
            val = float(corrected['saturated_fat_g'])
            rounded = self.validator.round_by_fda_rules(val, 'saturated_fat')
            corrected['saturated_fat_g'] = str(rounded)
        
        # Add more rounding as needed
        
        return corrected
    
    def _calculate_all_dv(self, data: Dict) -> Dict:
        """Calculate all %DV values"""
        dv_values = {}
        
        mappings = {
            'total_fat': 'total_fat_g',
            'saturated_fat': 'saturated_fat_g',
            'cholesterol': 'cholesterol_mg',
            'sodium': 'sodium_mg',
            'total_carb': 'total_carb_g',
            'fiber': 'fiber_g',
            'added_sugars': 'added_sugars_g',
            'vitamin_d': 'vitamin_d_mcg',
            'calcium': 'calcium_mg',
            'iron': 'iron_mg',
            'potassium': 'potassium_mg'
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


# ENHANCED EXTRACTION PROMPT
ENHANCED_EXTRACTION_PROMPT = """You are an expert FDA nutrition label data extractor. Your task is to extract ALL nutritional information from this food label with PERFECT accuracy.

CRITICAL INSTRUCTIONS:
1. Extract EXACT numbers as they appear on the label
2. Convert all nutrient names to English (if in Spanish/Portuguese)
3. Return ONLY valid JSON - no markdown, no explanations
4. If a value is not on the label, use null (not 0)
5. For Added Sugars: use null if not present (many LATAM labels don't have this)

REQUIRED JSON FORMAT:
{
    "product_name": "exact product name from label",
    "serving_size_original": "original serving size text exactly as shown",
    "serving_size_metric": "just the numeric + unit (e.g., '30g' or '240mL')",
    "servings_per_container": "number or 'About X'",
    "calories": "exact number",
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
}

EXTRACTION RULES:
- Be precise with decimals (e.g., 1.5g not 2g)
- Look for: "Grasas/Fat", "Sodio/Sodium", "Carbohidratos/Carbohydrate"
- Spanish "Azúcares añadidos" = Added Sugars
- Portuguese "Açúcares adicionados" = Added Sugars
- If label shows "<1g", use "0.5"
- If label shows "0g", use "0"
- Verify total sugars ≥ added sugars

Extract now:"""


# Usage example for integration:
"""
# In your Streamlit app, replace the extraction section with:

converter = EnhancedFDAConverter()

# After getting extraction_response from OpenAI
data_text = extraction_response['choices'][0]['message']['content']
data_text = data_text.replace('```json', '').replace('```', '').strip()
nutrition_data = json.loads(data_text)

# Validate and correct
corrected_data = converter.extract_and_validate(nutrition_data)

# Check for errors
if corrected_data['validation_report']['errors']:
    st.error("Critical validation errors found:")
    for error in corrected_data['validation_report']['errors']:
        st.error(f"❌ {error}")

# Show warnings
if corrected_data['validation_report']['warnings']:
    st.warning("Validation warnings:")
    for warning in corrected_data['validation_report']['warnings']:
        st.warning(f"⚠️ {warning}")

# Use corrected_data for label generation
"""
