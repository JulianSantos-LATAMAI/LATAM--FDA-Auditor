import streamlit as st
import base64
import os
from openai import OpenAI
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="FDA Label Compliance Auditor",
    page_icon="🏷️",
    layout="wide"
)

# Title and description
st.title("🏷️ FDA Label Compliance Auditor")
st.markdown("""
Upload a food label image to audit it against FDA regulations. 
The AI will analyze visual elements like font sizes, bolding, and content placement.
""")

# Load API key from Streamlit secrets
try:
    api_key = st.secrets["OPENAI_API_KEY"]
    api_key_loaded = True
except (KeyError, FileNotFoundError):
    api_key = None
    api_key_loaded = False

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    if api_key_loaded:
        st.success("✅ API Key loaded from secrets")
    else:
        st.error("❌ API Key not found in secrets")
        st.info("""
        **To add your API key:**
        
        1. In Streamlit Cloud: Go to app settings → Secrets
        2. Locally: Create `.streamlit/secrets.toml` with:
        ```
        OPENAI_API_KEY = "sk-your-key-here"
        ```
        """)
    
    st.markdown("---")
    st.markdown("""
    ### How it works:
    1. Upload a food label image
    2. Click 'Analyze Label'
    3. Review compliance results
    """)
    st.markdown("---")
    st.caption("Powered by GPT-4o Vision")

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Label")
    uploaded_file = st.file_uploader(
        "Choose a label image",
        type=["jpg", "jpeg", "png"],
        help="Upload a clear image of the nutrition label"
    )
    
    if uploaded_file:
        st.image(uploaded_file, caption="Uploaded Label", use_column_width=True)

with col2:
    st.subheader("📋 Compliance Analysis")
    
    # Check if rules file exists
    rules_file = Path("nutrition_rules.txt")
    if rules_file.exists():
        st.success(f"✅ Rules file loaded: {rules_file.name}")
        with st.expander("View Rules"):
            rules_content = rules_file.read_text()
            st.text(rules_content)
    else:
        st.error("❌ nutrition_rules.txt not found in the current directory")
        st.info("Please create a nutrition_rules.txt file with your FDA regulations")

# Analysis button
analyze_button_disabled = not (uploaded_file and api_key_loaded)

if st.button("🔍 Analyze Label", type="primary", disabled=analyze_button_disabled):
    if not uploaded_file:
        st.warning("Please upload a label image")
    elif not api_key_loaded:
        st.error("Please configure your OpenAI API key in Streamlit secrets")
    elif not rules_file.exists():
        st.error("nutrition_rules.txt file is missing")
    else:
        with st.spinner("Analyzing label against FDA regulations..."):
            try:
                # Read the rules file
                rules_content = rules_file.read_text()
                
                # Encode image to base64
                image_bytes = uploaded_file.read()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                # Determine image type
                image_type = uploaded_file.type
                
                # Initialize OpenAI client
                client = OpenAI(api_key=api_key)
                
                # Create the system prompt
                system_prompt = f"""You are an expert FDA Compliance Officer. I will provide a set of strict rules. You must analyze the provided image. If the label violates a rule, cite the specific rule tag (e.g., [RULE: FONT_SIZES]) and explain the error. If it passes, say 'PASS'. Be extremely strict.

FDA REGULATIONS:
{rules_content}"""
                
                # Make API call
                response = client.chat.completions.create(
                    model="gpt-4o",
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
                                    "text": "Please analyze this nutrition label for FDA compliance based on the rules provided."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{image_type};base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=2000,
                    temperature=0.1
                )
                
                # Extract and display the analysis
                analysis = response.choices[0].message.content
                
                st.markdown("---")
                st.subheader("🔎 Audit Results")
                
                # Display with nice formatting
                if "PASS" in analysis and len(analysis) < 50:
                    st.success("✅ Label is compliant!")
                else:
                    st.warning("⚠️ Compliance issues detected")
                
                st.markdown(analysis)
                
                # Add download button for report
                st.download_button(
                    label="📥 Download Report",
                    data=analysis,
                    file_name="compliance_report.txt",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.info("Please check your API key configuration and try again")

# Footer
st.markdown("---")
st.caption("⚠️ This tool provides AI-powered analysis for informational purposes. Always consult with regulatory experts for official compliance verification.")
