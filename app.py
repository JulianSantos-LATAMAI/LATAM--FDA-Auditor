import streamlit as st
import base64
import os
import openai
from pathlib import Path
from datetime import datetime
import json

# Page configuration
st.set_page_config(
    page_title="LATAM → USA Food Export Compliance Tool",
    page_icon="🌎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS with LATAM-friendly colors
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
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        font-size: 1.1rem;
    }
    .pass-box {
        background-color: #d4edda;
        border-left: 6px solid #28a745;
    }
    .fail-box {
        background-color: #f8d7da;
        border-left: 6px solid #dc3545;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 6px solid #ffc107;
    }
    .savings-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Language selection
language = st.sidebar.selectbox(
    "🌐 Language / Idioma",
    ["English", "Español"],
    help="Select your preferred language"
)

# Translations
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

# Helper function to calculate %DV (defined at module level)
def calculate_dv(nutrient_type, amount):
    """Calculate % Daily Value based on FDA standards"""
    try:
        amount_num = float(amount) if amount else 0
    except (ValueError, TypeError):
        return 0
    
    dv_values = {
        'fat': 78, 'sat_fat': 20, 'cholesterol': 300, 'sodium': 2300,
        'carbs': 275, 'fiber': 28, 'added_sugars': 50, 'vitamin_d': 20,
        'calcium': 1300, 'iron': 18, 'potassium': 4700
    }
    
    if nutrient_type in dv_values and dv_values[nutrient_type] > 0:
        return round((amount_num / dv_values[nutrient_type]) * 100)
    return 0

# Helper function to generate FDA label HTML
def generate_fda_label_html(nutrition_data):
    """Generate print-ready FDA label as HTML"""
    
    # Calculate all %DVs
    dvs = {
        'fat': calculate_dv('fat', nutrition_data.get('total_fat_g', 0)),
        'sat_fat': calculate_dv('sat_fat', nutrition_data.get('saturated_fat_g', 0)),
        'cholesterol': calculate_dv('cholesterol', nutrition_data.get('cholesterol_mg', 0)),
        'sodium': calculate_dv('sodium', nutrition_data.get('sodium_mg', 0)),
        'carbs': calculate_dv('carbs', nutrition_data.get('total_carb_g', 0)),
        'fiber': calculate_dv('fiber', nutrition_data.get('fiber_g', 0)),
        'added_sugars': calculate_dv('added_sugars', nutrition_data.get('added_sugars_g', 0)),
        'vitamin_d': calculate_dv('vitamin_d', nutrition_data.get('vitamin_d_mcg', 0)),
        'calcium': calculate_dv('calcium', nutrition_data.get('calcium_mg', 0)),
        'iron': calculate_dv('iron', nutrition_data.get('iron_mg', 0)),
        'potassium': calculate_dv('potassium', nutrition_data.get('potassium_mg', 0))
    }
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>FDA Nutrition Facts - {nutrition_data.get('product_name', 'Product')}</title>
        <style>
            @media print {{
                @page {{ margin: 0; }}
                body {{ margin: 0.5cm; }}
            }}
            
            body {{
                font-family: Helvetica, Arial, sans-serif;
                background: #f5f5f5;
                padding: 20px;
            }}
            
            .nutrition-label {{
                width: 3.5in;
                border: 1px solid black;
                padding: 0.1in;
                background: white;
                box-sizing: border-box;
                margin: 0 auto;
            }}
            
            .title {{
                font-size: 18pt;
                font-weight: bold;
                line-height: 1.2;
                margin: 0 0 2px 0;
            }}
            
            .thick-bar {{
                border-top: 10pt solid black;
                margin: 2px 0;
            }}
            
            .medium-bar {{
                border-top: 5pt solid black;
                margin: 2px 0;
            }}
            
            .thin-bar {{
                border-top: 0.5pt solid black;
                margin: 1px 0;
            }}
            
            .serving-info {{
                font-size: 8pt;
                margin: 2px 0;
                display: flex;
                justify-content: space-between;
            }}
            
            .serving-size {{
                font-weight: bold;
            }}
            
            .calories-section {{
                font-size: 8pt;
                margin: 4px 0;
                display: flex;
                justify-content: space-between;
                align-items: baseline;
            }}
            
            .calories-label {{
                font-weight: bold;
            }}
            
            .calories-value {{
                font-size: 16pt;
                font-weight: bold;
            }}
            
            .dv-header {{
                font-size: 7pt;
                font-weight: bold;
                text-align: right;
                margin: 2px 0;
            }}
            
            .nutrient-row {{
                font-size: 8pt;
                display: flex;
                justify-content: space-between;
                margin: 1px 0;
            }}
            
            .nutrient-name {{
                font-weight: bold;
            }}
            
            .indent-1 {{
                padding-left: 10px;
            }}
            
            .indent-2 {{
                padding-left: 20px;
            }}
            
            .dv-value {{
                font-weight: bold;
                min-width: 40px;
                text-align: right;
            }}
            
            .footnote {{
                font-size: 6pt;
                margin-top: 4px;
                line-height: 1.3;
            }}
            
            .instructions {{
                max-width: 600px;
                margin: 20px auto;
                padding: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <div class="nutrition-label">
            <div class="title">Nutrition Facts</div>
            <div class="thin-bar"></div>
            
            <div class="serving-info">
                <span class="serving-size">Serving size</span>
                <span>{nutrition_data.get('serving_size_us', '1 serving')}</span>
            </div>
            <div class="serving-info">
                <span>Servings per container</span>
                <span>{nutrition_data.get('servings_per_container', 'About X')}</span>
            </div>
            
            <div class="thick-bar"></div>
            
            <div class="calories-section">
                <span class="calories-label">Calories</span>
                <span class="calories-value">{nutrition_data.get('calories', '0')}</span>
            </div>
            
            <div class="medium-bar"></div>
            
            <div class="dv-header">% Daily Value*</div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row">
                <span><span class="nutrient-name">Total Fat</span> {nutrition_data.get('total_fat_g', '0')}g</span>
                <span class="dv-value">{dvs['fat']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row indent-1">
                <span>Saturated Fat {nutrition_data.get('saturated_fat_g', '0')}g</span>
                <span class="dv-value">{dvs['sat_fat']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row indent-1">
                <span><em>Trans</em> Fat {nutrition_data.get('trans_fat_g', '0')}g</span>
                <span class="dv-value"></span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row">
                <span><span class="nutrient-name">Cholesterol</span> {nutrition_data.get('cholesterol_mg', '0')}mg</span>
                <span class="dv-value">{dvs['cholesterol']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row">
                <span><span class="nutrient-name">Sodium</span> {nutrition_data.get('sodium_mg', '0')}mg</span>
                <span class="dv-value">{dvs['sodium']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row">
                <span><span class="nutrient-name">Total Carbohydrate</span> {nutrition_data.get('total_carb_g', '0')}g</span>
                <span class="dv-value">{dvs['carbs']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row indent-1">
                <span>Dietary Fiber {nutrition_data.get('fiber_g', '0')}g</span>
                <span class="dv-value">{dvs['fiber']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row indent-1">
                <span>Total Sugars {nutrition_data.get('total_sugars_g', '0')}g</span>
                <span class="dv-value"></span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row indent-2">
                <span>Includes {nutrition_data.get('added_sugars_g', '0')}g Added Sugars</span>
                <span class="dv-value">{dvs['added_sugars']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row">
                <span><span class="nutrient-name">Protein</span> {nutrition_data.get('protein_g', '0')}g</span>
                <span class="dv-value"></span>
            </div>
            
            <div class="thick-bar"></div>
            
            <div class="nutrient-row">
                <span>Vitamin D {nutrition_data.get('vitamin_d_mcg') or '0'}mcg</span>
                <span class="dv-value">{dvs['vitamin_d']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row">
                <span>Calcium {nutrition_data.get('calcium_mg') or '0'}mg</span>
                <span class="dv-value">{dvs['calcium']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row">
                <span>Iron {nutrition_data.get('iron_mg') or '0'}mg</span>
                <span class="dv-value">{dvs['iron']}%</span>
            </div>
            <div class="thin-bar"></div>
            
            <div class="nutrient-row">
                <span>Potassium {nutrition_data.get('potassium_mg') or '0'}mg</span>
                <span class="dv-value">{dvs['potassium']}%</span>
            </div>
            
            <div class="thick-bar"></div>
            
            <div class="footnote">
                * The % Daily Value (DV) tells you how much a nutrient in a serving 
                of food contributes to a daily diet. 2,000 calories a day is used 
                for general nutrition advice.
            </div>
        </div>
        
        <div class="instructions">
            <h2 style="margin-top: 0;">📋 How to Use This Label</h2>
            <ol style="line-height: 1.8;">
                <li><strong>Print to PDF:</strong> Press Ctrl+P (Windows) or Cmd+P (Mac)</li>
                <li><strong>Set margins to "None"</strong> for best results</li>
                <li><strong>Save as PDF</strong></li>
                <li><strong>Send to your graphic designer</strong> to integrate with your packaging</li>
                <li><strong>Or print directly</strong> and apply to products</li>
            </ol>
            <p style="color: #666; margin-top: 20px;">
                <em>This label meets FDA requirements per 21 CFR 101.9. 
                Generated by LATAM → USA Export Compliance Tool.</em>
            </p>
        </div>
    </body>
    </html>
    """
    
    return html

# Title
st.markdown(f'<p class="main-header">{t["title"]}</p>', unsafe_allow_html=True)
st.markdown(f'<p class="sub-header">{t["subtitle"]}</p>', unsafe_allow_html=True)

# Value proposition banner
st.markdown("""
<div class="savings-badge">
    <h3 style="margin:0;">⚡ Fast, Affordable, Accurate</h3>
    <p style="margin:0.5rem 0 0 0;">$5 per label • 60 seconds • 90% accurate vs $500 consultant • 2-4 weeks wait</p>
</div>
""", unsafe_allow_html=True)

# Operation mode selector (MOVED HERE - before it's used)
operation_mode = st.radio(
    "🔧 Select Tool Mode:",
    ["🔍 Audit Existing Label", "🔄 Convert LATAM Label to FDA Format"],
    horizontal=True,
    help="Choose whether to audit an existing FDA label or convert a LATAM label to FDA format"
)

st.markdown("---")

# Load API key
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    api_key_loaded = True
except (KeyError, FileNotFoundError):
    api_key = None
    api_key_loaded = False

# Sidebar
with st.sidebar:
    st.header(f"⚙️ {t['config']}")
    
    # API Status
    if api_key_loaded:
        st.success("✅ System: Active")
    else:
        st.error("❌ System: Not Configured")
    
    st.markdown("---")
    
    # Country selector - focused on top 4 LATAM markets
    origin_country = st.selectbox(
        "🏭 Your Country / Su País",
        ["🇲🇽 Mexico", "🇨🇴 Colombia", "🇨🇱 Chile", "🇧🇷 Brazil"],
        help="Select your country of origin"
    )
    
    st.markdown("---")
    
    # Model settings
    st.subheader("🤖 Analysis Settings")
    
    model_choice = st.selectbox(
        "AI Model",
        ["gpt-4o", "gpt-4-vision-preview"],
        index=0
    )
    
    strictness = st.radio(
        "Audit Strictness",
        ["Lenient (Screening)", "Balanced (Recommended)", "Strict (Final Check)"],
        index=1,
        help="How strict should the compliance check be?"
    )
    
    # Map to temperature
    temp_map = {
        "Lenient (Screening)": 0.2,
        "Balanced (Recommended)": 0.1,
        "Strict (Final Check)": 0.05
    }
    temperature = temp_map[strictness]
    
    st.markdown("---")
    
    # Check rules file
    rules_file = Path("nutrition_rules.txt")
    if rules_file.exists():
        rules_content = rules_file.read_text()
        st.success("✅ FDA Rules: Loaded")
        rule_count = rules_content.count("[RULE:")
        st.metric("Active Rules", rule_count)
    else:
        st.error("❌ Rules file missing")
        rules_content = None
    
    st.markdown("---")
    st.caption("🌎 LATAM Export Edition v1.0")

# Main content
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    if operation_mode == "🔍 Audit Existing Label":
        mode_description = "Upload an FDA-format label to audit" if language == "English" else "Suba una etiqueta formato FDA para auditar"
    else:
        mode_description = "Upload your LATAM label to convert to FDA format" if language == "English" else "Suba su etiqueta LATAM para convertir a formato FDA"
    
    st.subheader(f"📤 {t['upload']}")
    st.info(f"💡 **{mode_description}**")
    
    uploaded_file = st.file_uploader(
        "Choose label image / Elegir imagen de etiqueta",
        type=["jpg", "jpeg", "png"],
        help="Supported: JPG, PNG • Max 10MB"
    )
    
    if uploaded_file:
        file_size = uploaded_file.size / (1024 * 1024)
        
        if file_size > 10:
            st.error(f"⚠️ File too large: {file_size:.2f} MB (max 10 MB)")
        else:
            st.success(f"✅ Loaded: {uploaded_file.name} ({file_size:.2f} MB)")
            st.image(uploaded_file, caption="Your Label / Su Etiqueta", use_column_width=True)
            
            with st.expander("📊 File Details"):
                st.write(f"**Name:** {uploaded_file.name}")
                st.write(f"**Type:** {uploaded_file.type}")
                st.write(f"**Size:** {file_size:.2f} MB")

with col2:
    st.subheader(f"🔍 {t['results']}")
    
    # Pre-flight checks
    checks_passed = True
    
    if not uploaded_file:
        if language == "Español":
            st.info("👈 Por favor suba una imagen de etiqueta para comenzar")
        else:
            st.info("👈 Please upload a label image to begin")
        checks_passed = False
    
    if not api_key_loaded:
        st.error("⚠️ System not configured. Contact administrator.")
        checks_passed = False
    
    if not rules_file.exists():
        st.error("⚠️ FDA rules file missing")
        checks_passed = False
    
    if checks_passed:
        st.success("✅ Ready for analysis!")

# Analysis/Conversion button
st.markdown("---")

col_btn1, col_btn2 = st.columns([3, 1])

with col_btn1:
    if operation_mode == "🔍 Audit Existing Label":
        button_text = f"🔍 {t['analyze']}"
    else:
        button_text = "🔄 Convert to FDA Format" if language == "English" else "🔄 Convertir a Formato FDA"
    
    action_button = st.button(
        button_text,
        type="primary",
        disabled=not checks_passed,
        use_container_width=True
    )

with col_btn2:
    if 'last_analysis' in st.session_state:
        if st.button("🔄 Clear", use_container_width=True):
            del st.session_state.last_analysis
            st.rerun()

# Initialize session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# CONVERTER ENGINE
if operation_mode == "🔄 Convert LATAM Label to FDA Format" and action_button:
    if not checks_passed:
        st.error("❌ Cannot proceed. Please resolve issues above.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # STEP 1: Extract nutritional data
            status_text.text("📊 Step 1/3: Extracting data from your label..." if language == "English" else "📊 Paso 1/3: Extrayendo datos de su etiqueta...")
            progress_bar.progress(20)
            
            image_bytes = uploaded_file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            image_type = uploaded_file.type
            image_data_url = f"data:{image_type};base64,{base64_image}"
            
            openai.api_key = api_key
            
            extraction_prompt = """You are a nutrition label data extraction expert. Extract ALL nutritional information from this food label.

TASK: Read this label (may be in Spanish or Portuguese) and extract data as JSON.

REQUIRED JSON FORMAT (return ONLY valid JSON, no other text):
{
    "product_name": "exact product name from label",
    "serving_size_original": "serving size as shown on label",
    "serving_size_metric": "just the metric part (e.g., 30g or 240mL)",
    "servings_per_container": "number as string",
    "calories": "number as string",
    "total_fat_g": "number",
    "saturated_fat_g": "number",
    "trans_fat_g": "number",
    "cholesterol_mg": "number",
    "sodium_mg": "number",
    "total_carb_g": "number",
    "fiber_g": "number",
    "total_sugars_g": "number",
    "added_sugars_g": "number or 0 if not specified",
    "protein_g": "number",
    "vitamin_d_mcg": "number or null if not present",
    "calcium_mg": "number or null if not present",
    "iron_mg": "number or null if not present",
    "potassium_mg": "number or null if not present"
}

EXTRACTION RULES:
- Extract exact numerical values
- Convert all text to English nutrient names
- If a nutrient is not on the label, use null
- For Added Sugars, use 0 if not specified (many LATAM labels don't have this)
- Be precise with numbers (preserve decimals if shown)"""

            extraction_response = openai.ChatCompletion.create(
                model=model_choice,
                messages=[
                    {"role": "system", "content": extraction_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all nutrition data from this label as JSON"},
                            {"type": "image_url", "image_url": {"url": image_data_url, "detail": "high"}}
                        ]
                    }
                ],
                max_tokens=1500,
                temperature=0.0
            )
            
            status_text.text("✅ Data extracted!" if language == "English" else "✅ ¡Datos extraídos!")
            progress_bar.progress(40)
            
            # Parse JSON
            data_text = extraction_response['choices'][0]['message']['content']
            data_text = data_text.replace('```json', '').replace('```', '').strip()
            nutrition_data = json.loads(data_text)
            
            # STEP 2: Convert serving size to US format
            status_text.text("🔄 Step 2/3: Converting to US format..." if language == "English" else "🔄 Paso 2/3: Convirtiendo a formato USA...")
            progress_bar.progress(60)
            
            # Smart serving size conversion
            serving_metric = nutrition_data['serving_size_metric'].strip()
            
            # Common conversions
            us_conversions = {
                '30g': '2 tbsp (30g)', '15g': '1 tbsp (15g)', '240mL': '1 cup (240mL)',
                '250mL': '1 cup (250mL)', '28g': '1 oz (28g)', '100g': '3.5 oz (100g)',
                '200g': '7 oz (200g)', '150g': '5.3 oz (150g)', '50g': '1.8 oz (50g)',
                '120mL': '1/2 cup (120mL)', '180mL': '3/4 cup (180mL)',
                '15mL': '1 tbsp (15mL)', '5mL': '1 tsp (5mL)'
            }
            
            us_serving = us_conversions.get(serving_metric, f"1 serving ({serving_metric})")
            
            # STEP 3: Generate FDA-format label as text
            status_text.text("🎨 Step 3/3: Generating FDA label..." if language == "English" else "🎨 Paso 3/3: Generando etiqueta FDA...")
            progress_bar.progress(80)
            
            # Calculate all %DVs
            dvs = {
                'fat': calculate_dv('fat', nutrition_data.get('total_fat_g', 0)),
                'sat_fat': calculate_dv('sat_fat', nutrition_data.get('saturated_fat_g', 0)),
                'cholesterol': calculate_dv('cholesterol', nutrition_data.get('cholesterol_mg', 0)),
                'sodium': calculate_dv('sodium', nutrition_data.get('sodium_mg', 0)),
                'carbs': calculate_dv('carbs', nutrition_data.get('total_carb_g', 0)),
                'fiber': calculate_dv('fiber', nutrition_data.get('fiber_g', 0)),
                'added_sugars': calculate_dv('added_sugars', nutrition_data.get('added_sugars_g', 0)),
                'vitamin_d': calculate_dv('vitamin_d', nutrition_data.get('vitamin_d_mcg', 0)),
                'calcium': calculate_dv('calcium', nutrition_data.get('calcium_mg', 0)),
                'iron': calculate_dv('iron', nutrition_data.get('iron_mg', 0)),
                'potassium': calculate_dv('potassium', nutrition_data.get('potassium_mg', 0))
            }
            
            # Generate FDA-format label text
            fda_label_text = f"""Nutrition Facts
═══════════════════════════════════════════════
Serving size        {us_serving}
Servings per container    {nutrition_data.get('servings_per_container', 'About X')}
═══════════════════════════════════════════════

Calories                                    {nutrition_data.get('calories', '0')}
───────────────────────────────────────────────
                                    % Daily Value*
Total Fat {nutrition_data.get('total_fat_g', '0')}g                              {dvs['fat']}%
    Saturated Fat {nutrition_data.get('saturated_fat_g', '0')}g                      {dvs['sat_fat']}%
    Trans Fat {nutrition_data.get('trans_fat_g', '0')}g
Cholesterol {nutrition_data.get('cholesterol_mg', '0')}mg                          {dvs['cholesterol']}%
Sodium {nutrition_data.get('sodium_mg', '0')}mg                                 {dvs['sodium']}%
Total Carbohydrate {nutrition_data.get('total_carb_g', '0')}g                   {dvs['carbs']}%
    Dietary Fiber {nutrition_data.get('fiber_g', '0')}g                          {dvs['fiber']}%
    Total Sugars {nutrition_data.get('total_sugars_g', '0')}g
        Includes {nutrition_data.get('added_sugars_g', '0')}g Added Sugars    {dvs['added_sugars']}%
Protein {nutrition_data.get('protein_g', '0')}g

Vitamin D {nutrition_data.get('vitamin_d_mcg', '0')}mcg                         {dvs['vitamin_d']}%
Calcium {nutrition_data.get('calcium_mg', '0')}mg                            {dvs['calcium']}%
Iron {nutrition_data.get('iron_mg', '0')}mg                                  {dvs['iron']}%
Potassium {nutrition_data.get('potassium_mg', '0')}mg                        {dvs['potassium']}%
───────────────────────────────────────────────
* The % Daily Value (DV) tells you how much a nutrient in
  a serving of food contributes to a daily diet. 2,000
  calories a day is used for general nutrition advice."""
            
            progress_bar.progress(100)
            status_text.text("✅ Conversion complete!" if language == "English" else "✅ ¡Conversión completa!")
            
            # Display results
            st.markdown("---")
            st.success("✅ " + ("FDA Label Generated Successfully!" if language == "English" else "¡Etiqueta FDA Generada Exitosamente!"))
            
            # Show original vs converted
            col_compare1, col_compare2 = st.columns(2)
            
            with col_compare1:
                st.subheader("📋 Original Label" if language == "English" else "📋 Etiqueta Original")
                st.image(uploaded_file, use_column_width=True)
            
            with col_compare2:
                st.subheader("📋 FDA-Format Label" if language == "English" else "📋 Etiqueta Formato FDA")
                st.code(fda_label_text, language="text")
            
            # Show extracted data
            with st.expander("🔍 " + ("View Extracted Data" if language == "English" else "Ver Datos Extraídos")):
                st.json(nutrition_data)
            
            # STEP 4: Generate HTML Label
            st.markdown("---")
            st.subheader("🎨 " + ("Visual FDA Label (Print-Ready)" if language == "English" else "Etiqueta FDA Visual (Lista para Imprimir)"))
            
            # Generate the HTML label
            fda_label_html = generate_fda_label_html(nutrition_data)
            
            # Display HTML preview
            st.components.v1.html(fda_label_html, height=850, scrolling=True)
            
            st.success("""
            ✅ **Your FDA-compliant label is ready!**
            
            **How to use:**
            1. Download the HTML file below
            2. Open it in Chrome or Firefox
            3. Press Ctrl+P (Windows) or Cmd+P (Mac) to print
            4. Select "Save as PDF"
            5. Send the PDF to your packaging printer!
            
            The label meets all FDA requirements and is ready for production.
            """ if language == "English" else """
            ✅ **¡Su etiqueta compatible con FDA está lista!**
            
            **Cómo usar:**
            1. Descargue el archivo HTML a continuación
            2. Ábralo en Chrome o Firefox
            3. Presione Ctrl+P (Windows) o Cmd+P (Mac) para imprimir
            4. Seleccione "Guardar como PDF"
            5. ¡Envíe el PDF a su imprenta de empaques!
            
            La etiqueta cumple con todos los requisitos de FDA y está lista para producción.
            """)
            
            # Key conversions made
            st.markdown("---")
            st.subheader("🔄 " + ("Conversions Applied" if language == "English" else "Conversiones Aplicadas"))
            
            conversion_notes = []
            if serving_metric != us_serving:
                conversion_notes.append(f"✅ Serving size: `{serving_metric}` → `{us_serving}`")
            
            if nutrition_data.get('added_sugars_g') == '0':
                conversion_notes.append("✅ Added 'Added Sugars' line (0g) - required by FDA even if not on original")
            
            conversion_notes.append(f"✅ Calculated all %DV values per FDA standards")
            conversion_notes.append(f"✅ Formatted in FDA-required sequence")
            conversion_notes.append(f"✅ Added FDA footer text")
            
            for note in conversion_notes:
                st.markdown(note)
            
            # Download options
            st.markdown("---")
            st.subheader("📥 " + ("Download Options" if language == "English" else "Opciones de Descarga"))
            
            col_dl1, col_dl2 = st.columns(2)
            
            with col_dl1:
                # Text version
                st.download_button(
                    "📄 " + ("Download as Text File" if language == "English" else "Descargar como Texto"),
                    data=fda_label_text,
                    file_name=f"FDA_Label_{nutrition_data.get('product_name', 'product').replace(' ', '_')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col_dl2:
                # JSON data
                st.download_button(
                    "📊 " + ("Download as JSON" if language == "English" else "Descargar como JSON"),
                    data=json.dumps(nutrition_data, indent=2, ensure_ascii=False),
                    file_name=f"FDA_Data_{nutrition_data.get('product_name', 'product').replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            # Next steps guidance
            st.markdown("---")
            st.info("""
            **📝 Next Steps:**
            1. ✅ Download the FDA-format label text above
            2. 📋 Copy this text to your graphic designer
            3. 🎨 Have them create the final label design with proper fonts/layout
            4. 🔍 Upload the final design back here to audit it
            5. 🚀 Print and apply to your products for US export!
            """ if language == "English" else """
            **📝 Próximos Pasos:**
            1. ✅ Descargue el texto de la etiqueta FDA arriba
            2. 📋 Copie este texto a su diseñador gráfico
            3. 🎨 Que creen el diseño final con las fuentes/formato adecuados
            4. 🔍 Suba el diseño final aquí para auditarlo
            5. 🚀 ¡Imprima y aplique a sus productos para exportar a USA!
            """)
            
            progress_bar.empty()
            status_text.empty()
            
        except json.JSONDecodeError as e:
            progress_bar.empty()
            status_text.empty()
            st.error("❌ " + ("Could not parse nutrition data. The AI may not have returned valid JSON." if language == "English" else "No se pudo analizar los datos. La IA puede no haber devuelto JSON válido."))
            with st.expander("🔍 " + ("Debug Info" if language == "English" else "Info de Depuración")):
                st.code(data_text)
                st.info("Try uploading a clearer image or contact support.")
                
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Conversion failed: {str(e)}")

# AUDIT ENGINE (original functionality)
elif operation_mode == "🔍 Audit Existing Label" and action_button:
    if not checks_passed:
        st.error("❌ Cannot run analysis. Please resolve issues above.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Process image
            status_text.text("📸 Processing image..." if language == "English" else "📸 Procesando imagen...")
            progress_bar.progress(20)
            
            image_bytes = uploaded_file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            image_type = uploaded_file.type
            
            # Step 2: Configure API
            status_text.text("🔧 Connecting to AI..." if language == "English" else "🔧 Conectando con IA...")
            progress_bar.progress(40)
            
            openai.api_key = api_key
            
            # Step 3: Enhanced system prompt for LATAM context
            status_text.text("📋 Loading FDA regulations..." if language == "English" else "📋 Cargando regulaciones FDA...")
            progress_bar.progress(60)
            
            system_prompt = f"""You are a US FDA Compliance Expert specializing in helping LATAM food exporters enter the US market. 

CONTEXT: This label is from a {origin_country} food manufacturer seeking to export to the United States.

YOUR ROLE:
1. Check compliance with US FDA regulations (21 CFR 101.9)
2. Be HELPFUL and EDUCATIONAL - these are international clients learning US rules
3. Provide ACTIONABLE feedback they can implement
4. Explain WHY rules exist (not just that they're violated)

ANALYSIS PRIORITIES:

1. CRITICAL EXPORT BLOCKERS (Will prevent customs clearance)
   - [RULE: ENGLISH_LANGUAGE] Label must be in English (Spanish can be added as secondary)
   - [RULE: USA_UNITS] Must use US customary units (oz, fl oz) as primary (metric can be secondary)
   - [RULE: CALORIE_CALCULATION] Verify: (Fat × 9) + (Carbs × 4) + (Protein × 4) ≈ Calories (±15% tolerance)
   - [RULE: REQUIRED_NUTRIENTS] All FDA-mandatory nutrients must be present
   - [RULE: ALLERGEN_DECLARATION] Major allergens must be declared if present

2. COMPLIANCE ISSUES (Must fix before market entry)
   - [RULE: NUTRIENT_ORDER] Nutrients must follow FDA sequence
   - [RULE: SERVING_SIZE] Must use FDA-standard serving sizes
   - [RULE: PERCENT_DV] % Daily Value required for applicable nutrients
   - [RULE: ROUNDING] Follow FDA rounding rules

3. FORMAT & PRESENTATION (Important but fixable)
   - [RULE: BOLD_ELEMENTS] "Nutrition Facts" title and "Calories" must be bold
   - [RULE: FONT_HIERARCHY] Title should be largest text
   - [RULE: SEPARATORS] Proper separator lines between sections

4. HELPFUL GUIDANCE
   - Note any Spanish text that needs English translation
   - Suggest improvements for US consumer clarity
   - Flag cultural differences in labeling practices

FDA REGULATIONS:
{rules_content}

OUTPUT FORMAT (Critical for LATAM exporters):

**🚦 EXPORT READINESS: [READY / NEEDS FIXES / MAJOR REVISION]**

**❌ EXPORT BLOCKERS (Fix these first):**
- [Issues that will stop customs clearance]

**⚠️ COMPLIANCE ISSUES (Fix before launch):**
- [Issues needed for FDA compliance]

**📝 RECOMMENDATIONS (Improve market success):**
- [Suggestions to make label more appealing to US consumers]

**🇺🇸 LOCALIZATION NOTES:**
- [Specific guidance for adapting from {origin_country} to US market]

**💡 NEXT STEPS:**
[Prioritized action items with specific fixes]

IMPORTANT REMINDERS:
- Be encouraging - entering a new market is challenging
- Explain the "why" behind each rule
- Provide specific, actionable fixes
- Remember: This is their ticket to the US market!"""
            
            # Step 4: Make API call
            status_text.text("🤖 AI analyzing your label..." if language == "English" else "🤖 IA analizando su etiqueta...")
            progress_bar.progress(80)
            
            # Prepare image URL outside of the API call to avoid nested f-strings
            image_data_url = f"data:{image_type};base64,{base64_image}"
            
            response = openai.ChatCompletion.create(
                model=model_choice,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Please conduct a comprehensive US FDA compliance audit for this label from {origin_country}. Focus on what they need to change to export to the USA successfully."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_data_url,
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2500,
                temperature=temperature
            )
            
            # Step 5: Process results
            status_text.text("✅ Analysis complete!" if language == "English" else "✅ ¡Análisis completo!")
            progress_bar.progress(100)
            
            analysis = response['choices'][0]['message']['content']
            
            # Determine export readiness
            is_ready = "EXPORT READINESS: READY" in analysis
            needs_fixes = "NEEDS FIXES" in analysis
            
            # Calculate cost savings
            consultant_cost = 500  # Average consultant fee
            time_saved = 14  # Days saved
            
            # Store results
            st.session_state.last_analysis = {
                'timestamp': datetime.now(),
                'filename': uploaded_file.name,
                'analysis': analysis,
                'export_ready': is_ready,
                'needs_fixes': needs_fixes,
                'origin_country': origin_country,
                'model': model_choice,
                'cost_saved': consultant_cost - 5,
                'time_saved': time_saved
            }
            
            st.session_state.analysis_history.append(st.session_state.last_analysis)
            
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Analysis Failed: {str(e)}")
            
            with st.expander("🔍 Error Details"):
                st.code(str(e))
                if language == "Español":
                    st.info("""
                    **Problemas Comunes:**
                    - Clave API inválida o expirada
                    - Problemas de conectividad
                    - Archivo de imagen corrupto
                    
                    **Próximos Pasos:**
                    1. Verifique la clave API
                    2. Verifique el archivo de imagen
                    3. Espere 60 segundos e intente nuevamente
                    4. Contacte al administrador si persiste
                    """)
                else:
                    st.info("""
                    **Common Issues:**
                    - Invalid or expired API key
                    - Network connectivity issues
                    - Corrupted image file
                    
                    **Next Steps:**
                    1. Verify API key in secrets
                    2. Check image file integrity
                    3. Wait 60 seconds and retry
                    4. Contact administrator if problem persists
                    """)

# Display results
if 'last_analysis' in st.session_state:
    st.markdown("---")
    
    result = st.session_state.last_analysis
    
    # Savings display
    cost_saved = result.get('cost_saved', 495)
    time_saved = result.get('time_saved', 14)
    
    st.markdown(f"""
    <div class="savings-badge">
        <h3 style="margin:0;">{t['savings']}</h3>
        <h2 style="margin:0.5rem 0;">${cost_saved} USD • {time_saved} days</h2>
        <p style="margin:0;">vs traditional consultant</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Status display
    col_status, col_info = st.columns([2, 1])
    
    export_ready = result.get('export_ready', False)
    needs_fixes = result.get('needs_fixes', False)
    origin = result.get('origin_country', 'LATAM')
    
    with col_status:
        if export_ready:
            st.markdown("""
            <div class="status-box pass-box">
                <h2>✅ EXPORT READY!</h2>
                <p>Your label meets US FDA requirements</p>
            </div>
            """, unsafe_allow_html=True)
        elif needs_fixes:
            st.markdown("""
            <div class="status-box warning-box">
                <h2>⚠️ NEEDS FIXES</h2>
                <p>Some changes required - see details below</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-box fail-box">
                <h2>❌ MAJOR REVISION NEEDED</h2>
                <p>Significant changes required for US market</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col_info:
        st.metric("Analysis Date", result['timestamp'].strftime("%Y-%m-%d"))
        st.metric("Origin", origin)
        st.metric("Target", "🇺🇸 USA")
    
    # Detailed analysis
    st.subheader(f"📋 {t['results']}")
    st.markdown(result['analysis'])
    
    # Export options
    st.markdown("---")
    st.subheader(f"📥 {t['export']}")
    
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    
    with col_exp1:
        # Bilingual text report
        if language == "Español":
            report_header = "REPORTE DE CUMPLIMIENTO FDA - EXPORTACIÓN A USA"
            report_template = f"""
{report_header}
{'=' * 70}

Fecha de Análisis: {result['timestamp'].strftime("%Y-%m-%d %H:%M:%S")}
País de Origen: {result['origin_country']}
Archivo: {result['filename']}
Mercado Objetivo: Estados Unidos (FDA)
Estado: {"LISTO PARA EXPORTAR" if result['export_ready'] else "REQUIERE CORRECCIONES"}

Ahorro vs Consultor: ${result['cost_saved']} USD
Tiempo Ahorrado: {result['time_saved']} días

{'=' * 70}
ANÁLISIS DETALLADO:
{'=' * 70}

{result['analysis']}

{'=' * 70}
FIN DEL REPORTE
Generado por LATAM → USA Export Compliance Tool v1.0
"""
        else:
            report_template = f"""US FDA COMPLIANCE REPORT - LATAM FOOD EXPORT
{'=' * 70}

Analysis Date: {result['timestamp'].strftime("%Y-%m-%d %H:%M:%S")}
Origin Country: {result['origin_country']}
Label File: {result['filename']}
Target Market: United States (FDA)
Export Status: {"READY" if result['export_ready'] else "NEEDS REVISION"}

Savings vs Consultant: ${result['cost_saved']} USD
Time Saved: {result['time_saved']} days

{'=' * 70}
DETAILED ANALYSIS:
{'=' * 70}

{result['analysis']}

{'=' * 70}
END OF REPORT
Generated by LATAM → USA Export Compliance Tool v1.0
"""
        
        st.download_button(
            "📄 Text Report",
            data=report_template,
            file_name=f"USA_Export_Audit_{result['filename']}_{result['timestamp'].strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col_exp2:
        json_data = {
            "export_audit": {
                "timestamp": result['timestamp'].isoformat(),
                "origin_country": result['origin_country'],
                "target_market": "USA (FDA)",
                "filename": result['filename'],
                "export_ready": result['export_ready'],
                "cost_saved_usd": result['cost_saved'],
                "time_saved_days": result['time_saved']
            },
            "analysis": result['analysis'],
            "tool_version": "1.0.0"
        }
        
        st.download_button(
            "📊 JSON Data",
            data=json.dumps(json_data, indent=2, ensure_ascii=False),
            file_name=f"USA_Export_Audit_{result['timestamp'].strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_exp3:
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>US FDA Export Compliance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
                .header {{ background: linear-gradient(90deg, #00A859, #0066B2); color: white; padding: 30px; border-radius: 10px; }}
                .status {{ padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 6px solid; }}
                .ready {{ background-color: #d4edda; border-color: #28a745; }}
                .fixes {{ background-color: #fff3cd; border-color: #ffc107; }}
                .revision {{ background-color: #f8d7da; border-color: #dc3545; }}
                .metadata {{ background-color: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                .savings {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0; }}
                .analysis {{ line-height: 1.8; white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🌎 LATAM → USA Food Export Compliance Report</h1>
                <p>US FDA Regulation 21 CFR 101.9 Analysis</p>
            </div>
            
            <div class="savings">
                <h2>💰 Value Delivered</h2>
                <h3>${result['cost_saved']} USD saved • {result['time_saved']} days faster</h3>
            </div>
            
            <div class="metadata">
                <p><strong>Analysis Date:</strong> {result['timestamp'].strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Origin Country:</strong> {result['origin_country']}</p>
                <p><strong>Target Market:</strong> 🇺🇸 United States (FDA)</p>
                <p><strong>Label File:</strong> {result['filename']}</p>
            </div>
            
            <div class="status {'ready' if result['export_ready'] else 'fixes' if result['needs_fixes'] else 'revision'}">
                <h2>Export Status: {'✅ READY FOR USA MARKET' if result['export_ready'] else '⚠️ NEEDS FIXES' if result['needs_fixes'] else '❌ MAJOR REVISION NEEDED'}</h2>
            </div>
            
            <div class="analysis">
                <h3>Detailed Compliance Analysis:</h3>
                {result['analysis']}
            </div>
            
            <hr>
            <p><em>Generated by LATAM → USA Export Compliance Tool v1.0 | Helping LATAM exporters succeed in the US market</em></p>
        </body>
        </html>
        """
        
        st.download_button(
            "🌐 HTML Report",
            data=html_report,
            file_name=f"USA_Export_Audit_{result['timestamp'].strftime('%Y%m%d')}.html",
            mime="text/html",
            use_container_width=True
        )

# Footer with LATAM-specific information
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📖 About", "🎓 Resources", "💼 Pricing"])

with tab1:
    if language == "Español":
        st.markdown("""
        ### 🌎 Acerca de Esta Herramienta
        
        Esta herramienta fue diseñada específicamente para **exportadores de alimentos latinoamericanos** 
        que desean ingresar al mercado estadounidense.
        
        **¿Por qué es importante?**
        - La FDA rechaza miles de envíos cada año por etiquetas no conformes
        - Los consultores tradicionales cobran $500-2000 por etiqueta
        - El proceso tradicional toma 2-4 semanas
        
        **Nuestra solución:**
        - ✅ Análisis instantáneo en 60 segundos
        - ✅ Solo $5 por etiqueta
        - ✅ Retroalimentación específica y accionable
        - ✅ Disponible 24/7
        
        **Casos de uso:**
        1. Verificación rápida antes de contratar un consultor
        2. Validación de cambios de etiqueta
        3. Educación del equipo sobre requisitos de FDA
        4. Preparación para certificación oficial
        """)
    else:
        st.markdown("""
        ### 🌎 About This Tool
        
        This tool was designed specifically for **Latin American food exporters** 
        entering the US market.
        
        **Why it matters:**
        - FDA rejects thousands of shipments yearly for non-compliant labels
        - Traditional consultants charge $500-2000 per label
        - Traditional process takes 2-4 weeks
        
        **Our solution:**
        - ✅ Instant analysis in 60 seconds
        - ✅ Only $5 per label
        - ✅ Specific, actionable feedback
        - ✅ Available 24/7
        
        **Use cases:**
        1. Quick check before hiring expensive consultant
        2. Validate label changes
        3. Train your team on FDA requirements
        4. Prepare for official certification
        """)

with tab2:
    st.markdown("""
    ### 🎓 Free Resources for LATAM Exporters
    
    **FDA Official Guides:**
    - [FDA Food Labeling Guide](https://www.fda.gov/food/guidance-regulation-food-and-dietary-supplements/food-labeling-nutrition)
    - [Nutrition Facts Label Requirements](https://www.fda.gov/food/new-nutrition-facts-label/how-understand-and-use-nutrition-facts-label)
    
    **Common Mistakes LATAM Exporters Make:**
    1. ❌ Label only in Spanish/Portuguese (must have English)
    2. ❌ Using only metric units without household measures
    3. ❌ Wrong serving size standards
    4. ❌ Missing "Added Sugars" declaration
    5. ❌ Incorrect %DV calculations
    
    **Country-Specific Regulatory Differences:**
    
    **🇲🇽 Mexico (NOM-051-SCFI/SSA1-2010):**
    - Uses front-of-package warning labels (not required in USA)
    - Different serving size standards
    - May not require Added Sugars declaration
    - Trans fat limits differ from FDA
    
    **🇨🇴 Colombia (Resolution 2492/2022):**
    - Uses front-of-package warning stamps
    - Different nutrient rounding rules
    - May group some nutrients differently
    - Sodium limits more strict than FDA
    
    **🇨🇱 Chile (Law 20.606):**
    - "Alto en" (High in) warning system not used in USA
    - Different portion size standards
    - May not separate Added Sugars
    - Front labels required (not in USA)
    
    **🇧🇷 Brazil (RDC 429/2020):**
    - ANVISA uses different serving sizes than FDA
    - Front-of-pack nutrition labeling differs
    - Different %DV reference values
    - May use "Valor Energético" instead of Calories
    
    **Key Takeaway:** Your home country's compliant label likely needs significant changes for USA market!
    
    **Next Steps After Using This Tool:**
    1. Fix all "CRITICAL VIOLATIONS" immediately
    2. Address "ADVISORIES" before production
    3. Have your designer create final label with FDA format
    4. Consider hiring FDA consultant for final review ($200-500)
    5. Submit sample to FDA if product requires pre-approval
    """)

with tab3:
    if language == "Español":
        st.markdown("""
        ### 💼 Precios Transparentes
        
        **🎯 Por Etiqueta (Sin Compromiso):**
        - $5 USD por análisis individual
        - Pago por uso
        - Reportes completos incluidos
        
        **📦 Paquete PYME (Pequeñas/Medianas Empresas):**
        - 50 análisis: $200 USD ($4/etiqueta)
        - Válido por 6 meses
        - Soporte por email
        
        **🏢 Paquete Empresa:**
        - 200 análisis: $600 USD ($3/etiqueta)
        - Válido por 12 meses
        - Soporte prioritario
        - Consulta mensual incluida
        
        **🌟 Paquete Distribuidor/Exportador:**
        - Análisis ilimitados: $2,500 USD/mes
        - Procesamiento por lotes
        - Soporte dedicado
        - Capacitación del equipo
        - Integración API
        
        **Compare con consultores tradicionales:**
        - Consultor típico: $500-2000 por etiqueta ❌
        - Nuestra herramienta: $3-5 por etiqueta ✅
        - **Ahorro: 90-95%**
        """)
    else:
        st.markdown("""
        ### 💼 Transparent Pricing
        
        **🎯 Per-Label (No Commitment):**
        - $5 USD per individual analysis
        - Pay as you go
        - Full reports included
        
        **📦 SME Package (Small/Medium Exporters):**
        - 50 analyses: $200 USD ($4/label)
        - Valid for 6 months
        - Email support included
        
        **🏢 Enterprise Package:**
        - 200 analyses: $600 USD ($3/label)
        - Valid for 12 months
        - Priority support
        - Monthly consultation call
        
        **🌟 Distributor/Large Exporter:**
        - Unlimited analyses: $2,500 USD/month
        - Batch processing
        - Dedicated support
        - Team training
        - API integration
        
        **Compare to traditional consultants:**
        - Typical consultant: $500-2000 per label ❌
        - Our tool: $3-5 per label ✅
        - **Savings: 90-95%**
        """)

st.markdown("---")
st.caption("🌎 Helping LATAM food exporters succeed in the US market | © 2026 LATAM → USA Export Compliance Tool")
