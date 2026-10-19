import html
from datetime import datetime
import streamlit as st
import database as db

def esc(v): return html.escape(str(v if v not in (None, "") else "Not recorded"))
def fmt(d):
    try: return datetime.fromisoformat(str(d).replace("Z", "+00:00")).strftime("%b %d, %Y")
    except (ValueError, TypeError): return "Date not recorded"

def timeline(patient_id):
    data=db.records_for_patient(patient_id)
    events=[]
    for c in data.get("Consultations", []):
        ex=c.get("extracted") or {}
        if not isinstance(ex,dict): ex={}
        symptoms=ex.get("symptoms") or []
        if isinstance(symptoms,list): symptoms=", ".join(str(v) for v in symptoms)
        events.append((str(c.get("created_at") or ""),"Consultation",ex.get("summary") or symptoms or "Clinical note saved"))
    for a in data.get("Appointments", []):
        events.append((str(a.get("appointment_at") or a.get("created_at") or ""),"Appointment · "+str(a.get("status") or "Recorded"),a.get("reason") or "Follow-up visit"))
    events.sort(key=lambda x:x[0],reverse=True)
    if not events: st.info("No consultation or appointment events recorded for this patient."); return
    st.markdown('<div class="timeline">'+''.join(f'<div class="timeline-event"><div class="timeline-date">{esc(fmt(dt))} · {esc(kind)}</div><p>{esc(desc)}</p></div>' for dt,kind,desc in events)+'</div>',unsafe_allow_html=True)

st.title("Patient Records")
st.caption("Search by full or partial name. Verify date of birth before opening a patient chart.")
with st.form("patient_search"):
    left,right=st.columns([4,1],vertical_alignment="bottom")
    with left: name=st.text_input("Patient name",placeholder="Search Emily, Carter or Emi")
    with right: search=st.form_submit_button("Search",type="primary",use_container_width=True)
if search:
    try:
        st.session_state["patient_matches"]=db.search_patients_by_name(name)
        st.session_state["patient_searched"]=True
    except Exception as exc: st.error(f"Search failed: {exc}")
if st.session_state.get("patient_searched"):
    matches=st.session_state.get("patient_matches",[])
    st.caption(f"{len(matches)} matching patient(s)")
    if not matches: st.info("No matching patients found.")
    for patient in matches:
        with st.container(border=True):
            info,action=st.columns([5,1],vertical_alignment="center")
            with info:
                st.markdown(f"**{esc(patient.get('name') or 'Patient')}**")
                st.caption(f"DOB: {patient.get('dob') or 'Not recorded'} · ID: {patient['patient_id']}")
            with action:
                if st.button("Open Profile",key=f"open_{patient['patient_id']}",type="primary",use_container_width=True):
                    st.session_state["selected_patient_id"]=patient["patient_id"]
                    st.switch_page("pages/patient_detail.py")
    if len(matches)==1:
        with st.container(border=True):
            st.subheader("Clinical Timeline")
            try: timeline(matches[0]["patient_id"])
            except Exception as exc: st.warning(f"Timeline unavailable: {exc}")
    elif len(matches)>1:
        st.caption("Open a patient profile to see their individual clinical timeline.")
