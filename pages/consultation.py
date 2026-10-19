import asyncio
import streamlit as st
from shared import display_consultation_report, transcribe_audio, build_graph
st.title("Voice Consultation")
if st.session_state.pop("report_save_message", None):
    st.toast("Patient record saved. Check Patient Records for details.", icon="✅")
st.caption("Record the conversation, transcribe, and generate a patient report.")
with st.container(border=True):
    st.subheader("Record Conversation")
    audio=st.audio_input("Microphone",key="consultation_audio")
    if st.button("Transcribe Audio",type="primary",disabled=audio is None):
        try:
            with st.spinner("Transcribing..."):
                text=transcribe_audio(audio.getvalue(),"wav")
            st.session_state["transcript"]=text
            st.session_state["pending_report"]=None
            st.rerun()
        except Exception as exc: st.error(f"Transcription failed: {exc}")
with st.container(border=True):
    st.subheader("Conversation Transcript")
    transcript=st.text_area("Transcript",key="transcript",height=240)
    if st.button("Generate Report",type="primary",disabled=not transcript.strip(),use_container_width=True):
        try:
            with st.spinner("Generating report..."):
                result=asyncio.run(build_graph().ainvoke({"transcript":transcript,"patient_id":st.session_state.get("selected_patient_id","")}))
            if not result.get("extraction"): raise ValueError("No report data generated")
            st.session_state["pending_report"]=result
            st.session_state["pending_patient_id"]=st.session_state.get("selected_patient_id","")
            st.rerun()
        except Exception as exc: st.error(f"Unable to generate report: {exc}")
if st.session_state.get("pending_report"):
    display_consultation_report()
