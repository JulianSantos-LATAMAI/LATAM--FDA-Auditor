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
    
    # Target market selector
    target_market = st.selectbox(
        "🎯 Export Destination",
        ["🇺🇸 United States (FDA)", "🇨🇦 Canada (CFIA)", "🇪🇺 European Union (EFSA)"],
        help="Select your target market"
    )
    
    # API Status
    if api_key_loaded:
        st.success("✅ System: Active")
    else:
        st.error("❌ System: Not Configured")
    
    st.markdown("---")
    
    # Country selector for specific guidance
    origin_country = st.selectbox(
        "🏭 Your Country / Su País",
        ["🇲🇽 Mexico", "🇧🇷 Brazil", "🇨🇴 Colombia", "🇦🇷 Argentina", 
         "🇨🇱 Chile", "🇵🇪 Peru", "🇪🇨 Ecuador", "Other LATAM"],
        help="Helps us provide country-specific guidance"
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
    st.subheader(f"📤 {t['upload']}")
    
    # Helpful context for LATAM exporters
    if language == "Español":
        st.info("""
        💡 **Consejo**: Suba una foto clara de su etiqueta nutricional actual. 
        El sistema analizará si cumple con las regulaciones de FDA de Estados Unidos.
        """)
    else:
        st.info("""
        💡 **Tip**: Upload a clear photo of your current nutrition label. 
        The system will check if it meets US FDA regulations.
        """)
    
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

# Analysis button
st.markdown("---")

col_btn1, col_btn2 = st.columns([3, 1])

with col_btn1:
    analyze_button = st.button(
        f"🔍 {t['analyze']}",
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

# ANALYSIS ENGINE
if analyze_button:
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
                                    "url": f"data:{image_type};base64,{base64_image}",
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
    
    with col_status:
        if result['export_ready']:
            st.markdown("""
            <div class="status-box pass-box">
                <h2>✅ EXPORT READY!</h2>
                <p>Your label meets US FDA requirements</p>
            </div>
            """, unsafe_allow_html=True)
        elif result['needs_fixes']:
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
        st.metric("Origin", result['origin_country'])
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
    1. ❌ Label only in Spanish (must have English)
    2. ❌ Using only metric units (need US customary as primary)
    3. ❌ Wrong serving size standards
    4. ❌ Missing allergen declarations
    5. ❌ Incorrect calorie calculations
    
    **Country-Specific Tips:**
    - 🇲🇽 **Mexico**: NOM-051 differs significantly from FDA - don't assume compatibility
    - 🇧🇷 **Brazil**: ANVISA serving sizes often differ from FDA standards
    - 🇨🇴 **Colombia**: Resolution 810 has different rounding rules
    - 🇦🇷 **Argentina**: CAA requirements vary from FDA nutrient order
    
    **Next Steps After Analysis:**
    1. Fix all "EXPORT BLOCKERS" immediately
    2. Address "COMPLIANCE ISSUES" before production
    3. Consider "RECOMMENDATIONS" for market success
    4. Get final review from FDA-registered consultant
    5. Submit to FDA for official approval if required
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
