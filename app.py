import streamlit as st
import base64
import os
import openai
from pathlib import Path
from datetime import datetime
import json
import io

# Page configuration
st.set_page_config(
    page_title="FDA Label Compliance Auditor - Professional Edition",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional appearance
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f4788;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .pass-box {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }
    .fail-box {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<p class="main-header">🏛️ FDA Label Compliance Auditor</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Professional-Grade Nutrition Label Analysis System</p>', unsafe_allow_html=True)

# Load API key from Streamlit secrets
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    api_key_loaded = True
except (KeyError, FileNotFoundError):
    api_key = None
    api_key_loaded = False

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ System Configuration")
    
    # API Status
    if api_key_loaded:
        st.success("✅ API Key: Configured")
    else:
        st.error("❌ API Key: Not Found")
        with st.expander("🔧 API Key Setup Instructions"):
            st.markdown("""
            **For Streamlit Cloud:**
            1. Go to App Settings
            2. Navigate to Secrets
            3. Add:
            ```toml
            OPENAI_API_KEY = "sk-your-key-here"
            ```
            
            **For Local Development:**
            1. Create `.streamlit/secrets.toml`
            2. Add the same content
            3. Add to `.gitignore`
            """)
    
    # Model settings
    st.markdown("---")
    st.subheader("🤖 Model Configuration")
    
    model_choice = st.selectbox(
        "Vision Model",
        ["gpt-4o", "gpt-4-vision-preview"],
        help="Select the AI model for analysis"
    )
    
    temperature = st.slider(
        "Analysis Strictness",
        min_value=0.0,
        max_value=0.3,
        value=0.1,
        step=0.05,
        help="Lower = more strict and consistent"
    )
    
    max_tokens = st.number_input(
        "Max Response Tokens",
        min_value=500,
        max_value=4000,
        value=2000,
        step=100,
        help="Maximum length of analysis"
    )
    
    st.markdown("---")
    st.subheader("📋 Rules Configuration")
    
    # Check if rules file exists
    rules_file = Path("nutrition_rules.txt")
    if rules_file.exists():
        rules_content = rules_file.read_text()
        st.success(f"✅ Rules loaded ({len(rules_content)} chars)")
        
        with st.expander("📖 View Current Rules"):
            st.text_area("FDA Regulations", rules_content, height=300, disabled=True)
        
        # Rule statistics
        rule_count = rules_content.count("[RULE:")
        st.metric("Total Rules", rule_count)
    else:
        st.error("❌ nutrition_rules.txt not found")
        st.warning("Please upload nutrition_rules.txt to continue")
        rules_content = None
    
    st.markdown("---")
    st.caption("Version 1.0.0 | FDA Compliance Tool")

# Main content area
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📤 Label Upload")
    
    # File uploader with validation
    uploaded_file = st.file_uploader(
        "Upload Nutrition Label Image",
        type=["jpg", "jpeg", "png"],
        help="Supported formats: JPG, JPEG, PNG. Max size: 10MB",
        accept_multiple_files=False
    )
    
    if uploaded_file:
        # File validation
        file_size = uploaded_file.size / (1024 * 1024)  # Convert to MB
        
        if file_size > 10:
            st.error(f"⚠️ File too large: {file_size:.2f} MB (max 10 MB)")
        else:
            st.success(f"✅ File loaded: {uploaded_file.name} ({file_size:.2f} MB)")
            
            # Display image with info
            st.image(uploaded_file, caption="Uploaded Label", use_column_width=True)
            
            # Image metadata
            with st.expander("📊 Image Details"):
                st.write(f"**Filename:** {uploaded_file.name}")
                st.write(f"**Type:** {uploaded_file.type}")
                st.write(f"**Size:** {file_size:.2f} MB")

with col2:
    st.subheader("🔍 Compliance Analysis")
    
    # Pre-flight checks
    checks_passed = True
    
    if not uploaded_file:
        st.info("👈 Please upload a label image to begin analysis")
        checks_passed = False
    
    if not api_key_loaded:
        st.error("⚠️ API key not configured. Check sidebar for setup instructions.")
        checks_passed = False
    
    if not rules_file.exists():
        st.error("⚠️ Rules file (nutrition_rules.txt) is missing")
        checks_passed = False
    
    if checks_passed:
        st.success("✅ All systems ready for analysis")

# Analysis section
st.markdown("---")

# Analysis controls
col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])

with col_btn1:
    analyze_button = st.button(
        "🔍 Run Compliance Audit",
        type="primary",
        disabled=not checks_passed,
        use_container_width=True
    )

with col_btn2:
    if 'analysis_history' in st.session_state and len(st.session_state.analysis_history) > 0:
        if st.button("📜 View History", use_container_width=True):
            st.session_state.show_history = True

with col_btn3:
    if 'last_analysis' in st.session_state:
        if st.button("🔄 Clear Results", use_container_width=True):
            del st.session_state.last_analysis
            st.rerun()

# Initialize session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'show_history' not in st.session_state:
    st.session_state.show_history = False

# Analysis execution
if analyze_button:
    if not checks_passed:
        st.error("❌ Cannot run analysis. Please resolve all issues above.")
    else:
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Prepare image
            status_text.text("📸 Processing image...")
            progress_bar.progress(20)
            
            image_bytes = uploaded_file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            image_type = uploaded_file.type
            
            # Step 2: Configure API
            status_text.text("🔧 Configuring AI model...")
            progress_bar.progress(40)
            
            openai.api_key = api_key
            
            # Step 3: Create enhanced system prompt
            status_text.text("📋 Loading FDA regulations...")
            progress_bar.progress(60)
            
            system_prompt = f"""You are an FDA Compliance Assistant conducting a practical audit of a nutrition label. Your role is to identify CRITICAL errors that would require label rejection, while flagging borderline cases for human review.

ANALYSIS PRIORITIES (in order of importance):

1. CRITICAL MATHEMATICAL ERRORS
   - [RULE: CALORIE_CALCULATION] Verify calories = (Fat × 9) + (Carbs × 4) + (Protein × 4)
   - Allow ±10% tolerance for rounding
   - FAIL if discrepancy exceeds 10%

2. MANDATORY CONTENT ERRORS
   - [RULE: REQUIRED_NUTRIENTS] All mandatory nutrients must be present and in correct order
   - [RULE: ALLERGEN_DECLARATION] Cross-check ingredients vs "Contains" statement
   - [RULE: SERVING_SIZE] Must be declared and reasonable for product type
   - FAIL if any required element is missing

3. FORMATTING & SPELLING
   - [RULE: SPELLING] Check for misspellings (e.g., "Cholestrol" instead of "Cholesterol")
   - [RULE: UNITS] Verify correct units (g, mg, mcg) are used appropriately
   - [RULE: PERCENT_DV] % Daily Value must be shown for applicable nutrients
   - FAIL for obvious spelling errors

4. VISUAL HIERARCHY (Manual Check Zone)
   - [RULE: FONT_SIZES] You CANNOT measure exact point sizes from images
   - For fonts: If "Nutrition Facts" title looks substantially smaller than body text → FAIL
   - If fonts look reasonable but you're unsure of exact size → "⚠️ MANUAL CHECK: Verify font sizes meet FDA minimums"
   - DO NOT fail labels for font sizes unless they're obviously wrong

5. VISUAL FORMAT (Assessment Only)
   - [RULE: BOLD_ELEMENTS] Check if "Calories" and key elements appear bold
   - [RULE: SEPARATORS] Look for required separator lines
   - If missing → FAIL; If present but unclear → MANUAL CHECK

FDA REGULATIONS REFERENCE:
{rules_content}

OUTPUT FORMAT:
Structure your response as follows:

**COMPLIANCE STATUS: [PASS / FAIL / NEEDS REVIEW]**

**CRITICAL ISSUES (Must Fix):**
- [List only actual violations that require label rejection]

**WARNINGS (Manual Verification Needed):**
- [List borderline items that need human measurement/verification]

**ADVISORY NOTES (Optional Improvements):**
- [List minor suggestions that don't affect compliance]

DECISION RULES:
- Return "PASS" only if NO critical issues found
- Return "FAIL" if ANY critical mathematical, content, or spelling errors exist
- Return "NEEDS REVIEW" if only font/visual warnings exist
- Always be specific about WHAT is wrong and WHY it violates the rule"""
            
            # Step 4: Make API call
            status_text.text("🤖 Analyzing label with AI vision model...")
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
                                "text": "Conduct a comprehensive FDA compliance audit of this nutrition label. Check every requirement in the regulations provided."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_type};base64,{base64_image}",
                                    "detail": "high"  # High detail for better analysis
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Step 5: Process results
            status_text.text("✅ Analysis complete!")
            progress_bar.progress(100)
            
            analysis = response['choices'][0]['message']['content']
            
            # Determine compliance status
            is_compliant = "COMPLIANCE STATUS: PASS" in analysis or "NEEDS REVIEW" in analysis
            
            # Store in session state
            st.session_state.last_analysis = {
                'timestamp': datetime.now(),
                'filename': uploaded_file.name,
                'analysis': analysis,
                'compliant': is_compliant,
                'model': model_choice,
                'image_size': f"{file_size:.2f} MB"
            }
            
            # Add to history
            st.session_state.analysis_history.append(st.session_state.last_analysis)
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Analysis Failed: {str(e)}")
            
            # Detailed error logging
            with st.expander("🔍 Error Details (for troubleshooting)"):
                st.code(str(e))
                st.info("""
                **Common Issues:**
                - API key invalid or expired
                - Network connectivity issues
                - Image file corrupted
                - Rate limit exceeded
                
                **Next Steps:**
                1. Verify API key in secrets
                2. Check image file integrity
                3. Wait 60 seconds and retry
                4. Contact system administrator if problem persists
                """)

# Display results
if 'last_analysis' in st.session_state:
    st.markdown("---")
    
    result = st.session_state.last_analysis
    
    # Header with status
    col_status, col_info = st.columns([2, 1])
    
    with col_status:
        if result['compliant']:
            st.markdown("""
            <div class="status-box pass-box">
                <h2>✅ COMPLIANCE STATUS: PASS</h2>
                <p>Label meets all FDA requirements</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="status-box fail-box">
                <h2>❌ COMPLIANCE STATUS: FAIL</h2>
                <p>Label has regulatory violations</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col_info:
        st.metric("Analysis Date", result['timestamp'].strftime("%Y-%m-%d"))
        st.metric("Analysis Time", result['timestamp'].strftime("%H:%M:%S"))
        st.metric("Model Used", result['model'])
    
    # Detailed analysis
    st.subheader("📋 Detailed Audit Report")
    
    # Parse violations if failed
    if not result['compliant']:
        # Count violations by severity
        critical_count = result['analysis'].count("CRITICAL")
        major_count = result['analysis'].count("MAJOR")
        minor_count = result['analysis'].count("MINOR")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("🔴 Critical", critical_count)
        col2.metric("🟡 Major", major_count)
        col3.metric("🟢 Minor", minor_count)
    
    # Display full analysis
    st.markdown("**Full Analysis Report:**")
    st.markdown(result['analysis'])
    
    # Export options
    st.markdown("---")
    st.subheader("📥 Export Options")
    
    col_export1, col_export2, col_export3 = st.columns(3)
    
    with col_export1:
        # Text report
        report_text = f"""FDA LABEL COMPLIANCE AUDIT REPORT
{'=' * 60}

Analysis Date: {result['timestamp'].strftime("%Y-%m-%d %H:%M:%S")}
Label File: {result['filename']}
Image Size: {result['image_size']}
AI Model: {result['model']}
Compliance Status: {"PASS" if result['compliant'] else "FAIL"}

{'=' * 60}
DETAILED ANALYSIS:
{'=' * 60}

{result['analysis']}

{'=' * 60}
END OF REPORT
Generated by FDA Label Compliance Auditor v1.0
"""
        
        st.download_button(
            label="📄 Download Text Report",
            data=report_text,
            file_name=f"FDA_Audit_{result['filename']}_{result['timestamp'].strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col_export2:
        # JSON export
        json_data = {
            "audit_metadata": {
                "timestamp": result['timestamp'].isoformat(),
                "filename": result['filename'],
                "image_size": result['image_size'],
                "model": result['model'],
                "version": "1.0.0"
            },
            "compliance_status": "PASS" if result['compliant'] else "FAIL",
            "analysis": result['analysis']
        }
        
        st.download_button(
            label="📊 Download JSON Data",
            data=json.dumps(json_data, indent=2),
            file_name=f"FDA_Audit_{result['filename']}_{result['timestamp'].strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_export3:
        # PDF-ready HTML
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FDA Compliance Audit Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #1f4788; color: white; padding: 20px; }}
                .status {{ padding: 20px; margin: 20px 0; border-radius: 5px; }}
                .pass {{ background-color: #d4edda; border-left: 5px solid #28a745; }}
                .fail {{ background-color: #f8d7da; border-left: 5px solid #dc3545; }}
                .metadata {{ background-color: #f8f9fa; padding: 15px; margin: 20px 0; }}
                .analysis {{ line-height: 1.8; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>FDA Label Compliance Audit Report</h1>
            </div>
            
            <div class="metadata">
                <p><strong>Analysis Date:</strong> {result['timestamp'].strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p><strong>Label File:</strong> {result['filename']}</p>
                <p><strong>Image Size:</strong> {result['image_size']}</p>
                <p><strong>AI Model:</strong> {result['model']}</p>
            </div>
            
            <div class="status {'pass' if result['compliant'] else 'fail'}">
                <h2>Compliance Status: {'PASS ✓' if result['compliant'] else 'FAIL ✗'}</h2>
            </div>
            
            <div class="analysis">
                <h3>Detailed Analysis:</h3>
                <pre>{result['analysis']}</pre>
            </div>
            
            <hr>
            <p><em>Generated by FDA Label Compliance Auditor v1.0</em></p>
        </body>
        </html>
        """
        
        st.download_button(
            label="🌐 Download HTML Report",
            data=html_report,
            file_name=f"FDA_Audit_{result['filename']}_{result['timestamp'].strftime('%Y%m%d_%H%M%S')}.html",
            mime="text/html",
            use_container_width=True
        )

# Analysis history
if st.session_state.show_history and len(st.session_state.analysis_history) > 0:
    st.markdown("---")
    st.subheader("📜 Analysis History")
    
    for idx, record in enumerate(reversed(st.session_state.analysis_history[-10:])):  # Show last 10
        with st.expander(f"🗂️ {record['filename']} - {record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} - {'✅ PASS' if record['compliant'] else '❌ FAIL'}"):
            st.write(f"**Status:** {'PASS' if record['compliant'] else 'FAIL'}")
            st.write(f"**Model:** {record['model']}")
            st.write(f"**File:** {record['filename']}")
            st.markdown("**Analysis:**")
            st.text(record['analysis'][:500] + "..." if len(record['analysis']) > 500 else record['analysis'])
    
    if st.button("🗑️ Clear History"):
        st.session_state.analysis_history = []
        st.session_state.show_history = False
        st.rerun()

# Footer with important information
st.markdown("---")

col_footer1, col_footer2, col_footer3 = st.columns(3)

with col_footer1:
    st.markdown("""
    **🏛️ About This Tool**
    
    Professional FDA compliance auditor using advanced AI vision models to analyze nutrition labels against official FDA regulations (21 CFR 101.9).
    """)

with col_footer2:
    st.markdown("""
    **⚖️ Legal Notice**
    
    This tool provides AI-powered analysis for informational and screening purposes. Final compliance determinations must be made by qualified regulatory professionals. Not a substitute for legal review.
    """)

with col_footer3:
    st.markdown("""
    **📞 Support**
    
    For technical support, rule updates, or enterprise licensing inquiries, contact your system administrator.
    """)

st.caption("© 2026 FDA Label Compliance Auditor | Professional Edition v1.0.0 | Powered by GPT-4 Vision")
