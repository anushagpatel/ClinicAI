import streamlit as st
st.markdown("""<section class="hero"><div style="font-weight:700;letter-spacing:.11em;color:#a6e8e3;font-size:.78rem">CLINICAI · DOCTOR WORKSPACE</div><h1 style="margin:.55rem 0">Clinical notes, without the paperwork.</h1><p style="margin:0;font-size:1rem">Record consultations, review AI-generated notes, find patients and manage follow-ups in one workspace.</p></section>""", unsafe_allow_html=True)
a,b=st.columns([2,1])
with a:
    if st.button("🎙️ Start Voice Consultation",type="primary",use_container_width=True): st.switch_page("pages/consultation.py")
with b:
    if st.button("🔎 Find Patient",use_container_width=True): st.switch_page("pages/patient_records.py")
for col,heading,body in zip(st.columns(3),["🎤 Voice consultation","🗂️ Patient records","📅 Follow-up visits"],["Record audio and generate clinical notes.","Search records and review a clinical timeline.","Review and edit scheduled appointments."]):
    with col: st.markdown(f'<div class="feature"><b>{heading}</b><p style="margin:.4rem 0 0">{body}</p></div>',unsafe_allow_html=True)
st.caption("Synthetic-data demonstration · Clinical notes require doctor review.")
