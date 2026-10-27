import streamlit as st
from datetime import date
from pypdf import PdfReader, PdfWriter
import io
import base64
import requests
import json

# ============ CONFIG ============
XAI_API_KEY = "xai-5NEzWhbJ4lMdXHD9EBNK3ykphmoBs7ZnGUqMdvDwK5YEAsQw3FVKLMEjf7neWFytrXCj56IYvg8XBHG4"
# Move this to Streamlit secrets in production: st.secrets["XAI_API_KEY"]
# =================================

st.set_page_config(page_title="Empire State Tags • Form Tool", page_icon="🏷️", layout="centered")

if "step" not in st.session_state:
    st.session_state.step = 1
if "form_data" not in st.session_state:
    st.session_state.form_data = {}
if "extracted" not in st.session_state:
    st.session_state.extracted = {}

st.markdown("""
<style>
    .main { background-color: #f0f6fb; }
    h1 { color: #0a2f5c; font-weight: 700; }
    .stButton>button { 
        background-color: #0a2f5c; 
        color: white; 
        border-radius: 10px; 
        width: 100%; 
        font-weight: 600; 
        padding: 0.75rem;
        border: 2px solid #7eb6e0;
    }
    .step-indicator { font-weight: 700; color: #0a2f5c; margin-bottom: 12px; }
    .block-container { 
        border: 3px solid #7eb6e0; 
        border-radius: 16px; 
        padding: 20px; 
        background: white;
    }
</style>
""", unsafe_allow_html=True)

st.image("empire_state_tags_logo.jpg", width=180)
st.title("Empire State Tags")
st.caption("Internal Employee Tool • Virginia Forms • Extraction Tool")

def image_to_base64(file):
    if file is None:
        return None
    return base64.b64encode(file.getvalue()).decode()

def extract_with_grok(images_b64):
    if not images_b64:
        return {}
    content = [{"type": "text", "text": """Extract vehicle sale information from these documents (bill of sale, ID, title). Return ONLY valid JSON with these keys (use empty string if not found):
buyer_name, buyer_address, co_owner_name, year, make, model, vin, title_number, sale_date, price, odometer, seller_name, seller_address, lienholder, has_lien
Do not invent data. Only extract what is clearly visible."""}]
    for b64 in images_b64:
        if b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
            })
    try:
        resp = requests.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "grok-4.7",
                "messages": [{"role": "user", "content": content}],
                "max_tokens": 1500
            },
            timeout=90
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        st.info("AI response received")
        st.code(text[:800])
        if "```" in text:
            text = text.split("```")[1].replace("json", "").strip()
        return json.loads(text)
    except Exception as e:
        st.error(f"AI extraction failed: {e}")
        try:
            st.code(resp.text[:600])
        except:
            pass
        return {}

def fill_pdf(template_path, field_values):
    reader = PdfReader(template_path)
    writer = PdfWriter()
    writer.append(reader)
    if field_values:
        writer.update_page_form_field_values(writer.pages[0], field_values)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf

# STEP 1
if st.session_state.step == 1:
    st.markdown('<p class="step-indicator">Step 1 of 3 — Upload Documents</p>', unsafe_allow_html=True)
    st.info("Upload clear photos. The extraction tool will pull the information automatically.")

    col1, col2 = st.columns(2)
    with col1:
        bill = st.file_uploader("Bill of Sale", type=["jpg", "jpeg", "png"])
        id_photo = st.file_uploader("Customer ID", type=["jpg", "jpeg", "png"])
    with col2:
        title_front = st.file_uploader("Title – Front", type=["jpg", "jpeg", "png"])
        title_back = st.file_uploader("Title – Back", type=["jpg", "jpeg", "png"])

    if st.button("Extract & Continue", type="primary"):
        images = [image_to_base64(f) for f in [bill, id_photo, title_front, title_back] if f]
        with st.spinner("Reading documents..."):
            extracted = extract_with_grok(images)
        st.session_state.extracted = extracted
        st.session_state.form_data = extracted
        st.session_state.step = 2
        st.rerun()

# STEP 2
elif st.session_state.step == 2:
    st.markdown('<p class="step-indicator">Step 2 of 3 — Review & Correct</p>', unsafe_allow_html=True)
    st.info("AI extracted the information below. Correct anything wrong, then continue. Power of Attorney stays blank.")

    d = st.session_state.form_data
    with st.form("review_form"):
        buyer_name = st.text_input("Buyer Full Legal Name", value=d.get("buyer_name", ""))
        buyer_address = st.text_area("Buyer Address", value=d.get("buyer_address", ""))
        co_owner_name = st.text_input("Co-owner Name (leave blank if none)", value=d.get("co_owner_name", ""))
        year = st.text_input("Year", value=d.get("year", ""))
        make = st.text_input("Make", value=d.get("make", ""))
        model = st.text_input("Model", value=d.get("model", ""))
        vin = st.text_input("VIN", value=d.get("vin", ""))
        title_number = st.text_input("Title Number", value=d.get("title_number", ""))
        sale_date = st.text_input("Sale Date", value=d.get("sale_date", str(date.today())))
        price = st.number_input("Purchase Price ($)", min_value=0.0, value=float(d.get("price") or 0), step=100.0)
        odometer = st.number_input("Odometer", min_value=0, value=int(d.get("odometer") or 0))
        reg_period = st.radio("Registration Period", ["1 year", "2 years"], horizontal=True)
        lienholder = st.text_input("Lienholder (leave blank if none)", value=d.get("lienholder", ""))
        seller_name = st.text_input("Seller Name", value=d.get("seller_name", ""))
        seller_address = st.text_area("Seller Address", value=d.get("seller_address", ""))

        col_a, col_b = st.columns(2)
        with col_a:
            back = st.form_submit_button("← Back")
        with col_b:
            next_btn = st.form_submit_button("Next — Confirm", type="primary")

        if back:
            st.session_state.step = 1
            st.rerun()
        if next_btn:
            st.session_state.form_data = {
                "buyer_name": buyer_name, "buyer_address": buyer_address,
                "co_owner_name": co_owner_name, "year": year, "make": make,
                "model": model, "vin": vin, "title_number": title_number,
                "sale_date": sale_date, "price": price, "odometer": odometer,
                "reg_period": reg_period, "lienholder": lienholder,
                "seller_name": seller_name, "seller_address": seller_address,
            }
            st.session_state.step = 3
            st.rerun()

# STEP 3
elif st.session_state.step == 3:
    st.markdown('<p class="step-indicator">Step 3 of 3 — Confirm & Generate Forms</p>', unsafe_allow_html=True)
    d = st.session_state.form_data
    st.success("Review and generate the official Virginia forms.")

    st.markdown(f"""
**Buyer:** {d.get('buyer_name')}  
**Address:** {d.get('buyer_address')}  
**Vehicle:** {d.get('year')} {d.get('make')} {d.get('model')}  
**VIN:** {d.get('vin')}  
**Price:** ${d.get('price', 0):,.2f}  
**Sale Date:** {d.get('sale_date')}  
**Odometer:** {d.get('odometer')}  
**Lien:** {d.get('lienholder') or 'None'}  
**Seller:** {d.get('seller_name')}
    """)

    if st.button("Generate Official Forms", type="primary"):
        # VSA 17A
        vsa_fields = {
            "BusinessStreetAdd[0]": d.get("buyer_name", ""),
            "Year[0]": d.get("year", ""),
            "Make[0]": d.get("make", ""),
            "TextField1[0]": d.get("model", ""),
            "TextField1[2]": d.get("vin", ""),
            "SalesPrice[0]": str(int(d.get("price", 0))),
            "TextField2[0]": str(d.get("odometer", "")),
        }
        if d.get("co_owner_name"):
            vsa_fields["CoOwnerName[0]"] = d.get("co_owner_name")
        if d.get("lienholder"):
            vsa_fields["LienName[0]"] = d.get("lienholder")
        try:
            pdf = fill_pdf("VA_VSA_17A_Official.pdf", vsa_fields)
            st.download_button("Download Filled VSA 17A", pdf, file_name=f"VSA_17A_{d.get('buyer_name','x').replace(' ','_')}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"VSA 17A: {e}")

        # Price Certification
        price_fields = {
            "Text32[0]": d.get("buyer_name", ""),
            "Text32[2]": d.get("seller_name", ""),
            "Text32[4]": d.get("vin", ""),
            "Text32[6]": d.get("year", ""),
            "Text32[7]": d.get("make", ""),
            "Text32[8]": d.get("model", ""),
            "TextFieldnew[0]": str(int(d.get("price", 0))),
            "TextFieldnew[2]": str(int(d.get("price", 0))),
            "TextFieldnew[4]": d.get("sale_date", ""),
        }
        try:
            pdf = fill_pdf("VA_Vehicle_Price_Certification.pdf", price_fields)
            st.download_button("Download Filled Price Certification", pdf, file_name=f"Price_Cert_{d.get('buyer_name','x').replace(' ','_')}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Price Cert: {e}")

        # Blank VSA 70
        try:
            pdf = fill_pdf("VA_VSA_70_Official.pdf", {})
            st.download_button("Download Blank VSA 70 (Power of Attorney)", pdf, file_name="VSA_70_BLANK.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"VSA 70: {e}")

        st.info("VSA 70 left blank. Customer signs in office. Confirm lien release if needed.")

    if st.button("← Back"):
        st.session_state.step = 2
        st.rerun()
    if st.button("Start Over"):
        st.session_state.step = 1
        st.session_state.form_data = {}
        st.session_state.extracted = {}
        st.rerun()

st.divider()
st.caption("© 2026 Empire State Tags. All rights reserved. Internal use only. Power of Attorney always left blank.")
