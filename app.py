import streamlit as st
import google.generativeai as genai
import pdfplumber
import requests
from bs4 import BeautifulSoup
import re

# ==========================================
# 1. إعدادات الواجهة الاحترافية
# ==========================================
st.set_page_config(page_title="حاميك | الذكاء القانوني", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Tajawal', sans-serif !important; direction: rtl; text-align: right; }
    .stApp { background: linear-gradient(135deg, #0b1320 0%, #1a2a40 100%); color: #e2e8f0; }
    h1, h2, h3 { color: #d4af37 !important; font-weight: 900 !important; }
    [data-testid="stSidebar"] { background-color: rgba(11, 19, 32, 0.85) !important; border-left: 1px solid rgba(212, 175, 55, 0.2); }
    .stButton>button { background: linear-gradient(90deg, #0e7b6e 0%, #12a390 100%) !important; color: #ffffff !important; border-radius: 8px !important; border: 1px solid rgba(255,255,255,0.1) !important; font-weight: 700 !important; }
    .stChatMessage { background: rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 1.5rem; border: 1px solid rgba(255, 255, 255, 0.1); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. حماية الـ API KEY 
# ==========================================
# سنسحب المفتاح من إعدادات السيرفر لحمايته من السرقة
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
except KeyError:
    st.error("⚠️ يرجى إضافة GEMINI_API_KEY في إعدادات السيرفر.")
    st.stop()

# ==========================================
# 3. دوال قراءة وتنظيف النصوص
# ==========================================
def clean_arabic_text(text):
    if not text: return ""
    text = re.sub(r'[أإآ]', 'ا', text) 
    text = re.sub(r'ة', 'ه', text)     
    text = re.sub(r'[\u064B-\u065F]', '', text) 
    text = re.sub(r'\n+', '\n', text)  
    text = re.sub(r' +', ' ', text)    
    return text.strip()

def extract_text_from_pdf(pdf_file):
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                if page.extract_text(): text += page.extract_text() + "\n"
    except Exception:
        pass
    return clean_arabic_text(text)

def extract_text_from_url(url):
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        for script in soup(["script", "style", "header", "footer"]): script.extract()
        return clean_arabic_text(soup.get_text(separator=' ', strip=True))
    except Exception:
        return ""

def load_egyptian_law():
    try:
        with open("egyptian_privacy_law.txt", "r", encoding="utf-8") as f:
            return clean_arabic_text(f.read())
    except Exception:
        return "لم يتم العثور على ملف القانون."

# ==========================================
# 4. إعداد العقل المدبر (Gemini Prompt)
# ==========================================
LAW_TEXT = load_egyptian_law()

SYSTEM_INSTRUCTION = f"""
أنت نظام ذكي ومستشار قانوني مصري رفيع المستوى تُدعى "حاميك".
أنت متخصص حصرياً في "قانون حماية البيانات الشخصية المصري رقم 151 لسنة 2020" ولائحته التنفيذية وتفسيراته.

تعليماتك الصارمة:
1. تحدث دائماً بـ "لغة عربية فصحى" مبسطة جداً للمواطن العادي.
2. كن حاسماً: هل السياسة تحمي المستخدم أم تستغله؟ اذكر ذلك بوضوح.
3. استند في تحليلك لـ "القانون المصري" الذي تمت تغذيتك به، واذكر مدى امتثال السياسة لهذا القانون.
4. استخدم التنسيق المنظم والرموز التعبيرية (⚖️، ⚠️، ✅، ❌).

قاعدة بياناتك القانونية المرجعية:
---
{LAW_TEXT}
---
"""

model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest', system_instruction=SYSTEM_INSTRUCTION)

# ==========================================
# 5. بناء واجهة الموقع
# ==========================================
st.markdown("<div style='text-align: center; padding: 2rem 0;'><h1 style='font-size: 3.5rem;'>⚖️ حــــامِــــيــــك</h1><h3 style='color: #0e7b6e;'>الذكاء الاصطناعي لتقييم الامتثال القانوني لسياسات الخصوصية</h3></div>", unsafe_allow_html=True)
st.divider()

if "chat_session" not in st.session_state: st.session_state.chat_session = None
if "messages" not in st.session_state: st.session_state.messages =[]
if "policy_loaded" not in st.session_state: st.session_state.policy_loaded = False

with st.sidebar:
    st.markdown("<h2 style='text-align:center;'>📄 إدراج السياسة</h2>", unsafe_allow_html=True)
    input_method = st.radio("اختر آلية الإدخال:", ("رابط إلكتروني (URL)", "ملف وثيقة (PDF)"))
    
    policy_text = ""
    if input_method == "ملف وثيقة (PDF)":
        uploaded_file = st.file_uploader("قم برفع الملف", type=["pdf"])
        if st.button("بدء التحليل 🔍") and uploaded_file:
            with st.spinner('جاري استخلاص النصوص...'):
                policy_text = extract_text_from_pdf(uploaded_file)
    elif input_method == "رابط إلكتروني (URL)":
        url = st.text_input("أدخل الرابط:")
        if st.button("بدء التحليل 🔍") and url:
            with st.spinner('جاري استخلاص النصوص من الشبكة...'):
                policy_text = extract_text_from_url(url)
    
    if policy_text:
        if len(policy_text) < 50:
            st.error("النص المستخرج غير كافٍ للتحليل.")
        else:
            st.success("✅ تمت قراءة الوثيقة بنجاح.")
            st.session_state.policy_loaded = True
            st.session_state.chat_session = model.start_chat(history=[
                {"role": "user", "parts":[f"هذه سياسة الخصوصية المراد تقييمها وفقاً للقانون المصري المرفق في تعليماتك:\n\n{policy_text}"]},
                {"role": "model", "parts":["تم الاستلام والمطابقة مع قانون 151 لسنة 2020. أنا جاهز للإجابة."]}
            ])
            st.session_state.messages =[{"role": "assistant", "content": "أهلاً بك في منصة **حاميك** ⚖️.\nلقد أتممت دراسة سياسة الخصوصية. هل تود معرفة إذا كانوا يبيعون بياناتك؟ أم تريد تقريراً عن مدى التزامهم بالقانون المصري؟"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not st.session_state.policy_loaded:
    st.info("👈 يُرجى إدراج سياسة الخصوصية عبر القائمة الجانبية لتفعيل المستشار القانوني.")
else:
    if prompt := st.chat_input("اكتب استفسارك القانوني هنا..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            msg_placeholder = st.empty()
            with st.spinner("جاري صياغة الرد القانوني... ⚖️"):
                try:
                    response = st.session_state.chat_session.send_message(prompt)
                    msg_placeholder.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    msg_placeholder.error(f"خطأ: {e}")
