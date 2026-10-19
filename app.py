"""ClinicAI multipage portal. Synthetic data only."""
import streamlit as st
st.set_page_config(page_title="ClinicAI | Doctor Workspace", page_icon="🩺", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
.stApp {background:#f6f9fb;color:#173447}
.block-container {max-width:1500px;padding-top:.65rem;padding-bottom:.5rem}
[data-testid="stHeader"] {background:transparent}
[data-testid="stSidebar"] {display:none}
h1,h2,h3 {color:#173447;letter-spacing:-.025em}
.stButton>button {border-radius:11px}
.stButton>button[kind="primary"] {background:#087f8c;border-color:#087f8c}
[data-testid="stVerticalBlockBorderWrapper"]>div {border-radius:17px}
.brand {font-size:1.55rem;font-weight:800;color:#07566b}
.brand span {color:#16aa9e}
.hero {background:linear-gradient(120deg,#073f56,#0b8391);color:white;border-radius:20px;padding:26px 32px;margin:8px 0 12px}
.hero h1 {color:white;font-size:clamp(1.7rem,3vw,2.7rem);line-height:1.15}
.hero p {color:#e0f4f5;font-size:1.1rem;max-width:640px}
.feature {background:white;border:1px solid #dce7ec;border-radius:14px;padding:14px;min-height:100px}
.feature b {font-size:1.1rem}.feature p {color:#597180}
[data-testid="stMainBlockContainer"] {padding-top:.65rem}
[data-testid="stMain"] {overflow-x:hidden}
[data-testid="stPageLink"] {border-radius:10px}
[data-testid="stSidebar"] {display:none}
.compact-kpi {padding:12px 16px;background:white;border:1px solid #dce7ec;border-radius:14px}
.compact-kpi small {color:#607a8a}
.timeline {max-height:52vh;overflow-y:auto;padding-right:8px}
.timeline-event {border-left:3px solid #0b8391;padding:10px 14px;margin:0 0 12px 9px;background:#fff;border-radius:0 12px 12px 0;border-top:1px solid #e0e9ed;border-right:1px solid #e0e9ed;border-bottom:1px solid #e0e9ed}
.timeline-date {color:#087f8c;font-size:.8rem;font-weight:700}
.timeline-event p {margin:4px 0;color:#4c6472}
@media(max-width:850px){.hero{padding:18px}.feature{min-height:0}}
</style>""",unsafe_allow_html=True)
# True multipage routing: only Home, Consultation and Patient Records are visible in top navigation.
pg = st.navigation([
    st.Page("pages/home.py", title="Home", icon="🏠", url_path="home", default=True),
    st.Page("pages/consultation.py", title="Consultation", icon="🎙️", url_path="consultation"),
    st.Page("pages/patient_records.py", title="Patient Records", icon="📋", url_path="patient-records"),
    st.Page("pages/patient_detail.py", title="Patient Profile", icon="👤", url_path="patient-profile"),
], position="hidden")
brand, links, menu = st.columns([1.25,3.2,.4],vertical_alignment="center")
with brand:
    st.markdown('<div class="brand">✚ Clinic<span>AI</span></div><small>DOCTOR CONSULTATION WORKSPACE</small>',unsafe_allow_html=True)
with links:
    a,b,c=st.columns(3)
    with a: st.page_link("pages/home.py",label="Home",icon="🏠",use_container_width=True)
    with b: st.page_link("pages/consultation.py",label="Consultation",icon="🎙️",use_container_width=True)
    with c: st.page_link("pages/patient_records.py",label="Patient Records",icon="📋",use_container_width=True)
with menu:
    with st.popover("☰", help="Workspace menu"):
        st.page_link("pages/home.py", label="Home", icon="🏠")
        st.page_link("pages/consultation.py", label="Consultation", icon="🎙️")
        st.page_link("pages/patient_records.py", label="Patient Records", icon="📋")
        if st.session_state.get("selected_patient_id"):
            st.page_link("pages/patient_detail.py", label="Current Patient", icon="👤")
pg.run()
