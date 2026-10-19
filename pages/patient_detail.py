import html
from datetime import date,datetime
from zoneinfo import ZoneInfo
import streamlit as st
import database as db

def readable(value):
    if value is None or value=="" or value==[] or value=={}: return "Not recorded"
    if isinstance(value,dict): return "; ".join(f"{k.replace('_',' ').title()}: {readable(v)}" for k,v in value.items())
    if isinstance(value,list): return "; ".join(readable(v) for v in value)
    return str(value)
def esc(v): return html.escape(readable(v))
def pretty_date(v):
    try: return date.fromisoformat(str(v)[:10]).strftime("%b %d, %Y")
    except (ValueError,TypeError): return readable(v)
def local_time(v):
    try: return datetime.fromisoformat(str(v).replace("Z","+00:00")).astimezone(ZoneInfo("America/New_York")).strftime("%I:%M %p").lstrip("0")
    except (ValueError,TypeError): return "Not recorded"

patient_id=st.session_state.get("selected_patient_id")
if not patient_id:
    st.info("Find a patient first.")
    if st.button("Search Patients"): st.switch_page("pages/patient_records.py")
    st.stop()
try:
    patient=db.get("Patients",patient_id)
    if not patient: raise ValueError("Patient record not found")
    records=db.records_for_patient(patient_id)
except Exception as exc:
    st.error(f"Unable to load patient: {exc}"); st.stop()

@st.dialog("Edit Patient Information",width="large")
def edit_patient():
    with st.form("edit_profile"):
        a,b=st.columns(2)
        with a:
            name=st.text_input("Full name",value=patient.get("name") or "")
            dob=st.text_input("Date of birth (YYYY-MM-DD)",value=patient.get("dob") or "")
            age=st.number_input("Age",0,120,int(patient.get("age") or 0))
            phone=st.text_input("Phone",value=patient.get("phone") or "")
            insurer=st.text_input("Insurance",value=patient.get("insurance_company") or "")
        with b:
            email=st.text_input("Email",value=patient.get("email") or "")
            member=st.text_input("Insurance member ID",value=patient.get("insurance_member_id") or "")
            address=st.text_input("Address",value=patient.get("address") or "")
            allergies=st.text_area("Allergies",value=readable(patient.get("allergies")) if patient.get("allergies") else "")
            history=st.text_area("Medical history",value=readable(patient.get("medical_history")) if patient.get("medical_history") else "")
        save=st.form_submit_button("Save Changes",type="primary")
    if save:
        try:
            if not name.strip(): raise ValueError("Name required")
            if dob.strip(): date.fromisoformat(dob.strip())
            db.update_patient(patient_id,name.strip(),int(age))
            db.update_patient_details(patient_id,dob=dob.strip(),phone=phone,email=email,insurance_company=insurer,insurance_member_id=member,address=address,allergies=allergies,medical_history=history)
            st.rerun()
        except Exception as exc: st.error(f"Unable to save: {exc}")

@st.dialog("Edit Follow-up Appointment")
def edit_appointment(appointment):
    try: current=datetime.fromisoformat(appointment["appointment_at"]).astimezone(ZoneInfo("America/New_York"))
    except Exception: st.error("Invalid appointment date"); return
    with st.form("appointment_edit_form"):
        day=st.date_input("Appointment date",value=current.date())
        time=st.text_input("Time (12-hour)",value=current.strftime("%I:%M %p").lstrip("0"))
        reason=st.text_input("Reason",value=appointment.get("reason") or "Follow-up")
        submit=st.form_submit_button("Save Appointment",type="primary")
    if submit:
        try:
            from shared import parse_appointment_time
            new_dt=parse_appointment_time(day.isoformat(),time).replace(tzinfo=ZoneInfo("America/New_York"))
            db.reschedule_appointment(appointment["appointment_id"],patient_id,new_dt.isoformat(),reason.strip())
            st.rerun()
        except Exception as exc: st.error(f"Unable to reschedule: {exc}")

head,edit,back=st.columns([5,1,1],vertical_alignment="center")
with head:
    st.title(patient.get("name") or "Patient Profile")
    st.caption("Patient Profile · DOB: "+pretty_date(patient.get("dob")))
with edit:
    if st.button("✏️ Edit",type="primary",use_container_width=True): edit_patient()
with back:
    if st.button("← Search",use_container_width=True): st.switch_page("pages/patient_records.py")

left,right=st.columns([1.05,1.8],gap="medium")
with left:
    with st.container(border=True):
        st.subheader("Patient Details")
        for label,key in [("Date of birth","dob"),("Age","age"),("Phone","phone"),("Email","email"),("Insurance","insurance_company"),("Member ID","insurance_member_id"),("Allergies","allergies"),("Medical history","medical_history")]:
            st.markdown(f"<div style='margin:5px 0'><span style='color:#607a8a;font-size:.78rem'>{esc(label)}</span><div style='font-size:.94rem'>{esc(patient.get(key))}</div></div>",unsafe_allow_html=True)
    with st.container(border=True):
        st.subheader("Follow-up Appointments")
        appts=[a for a in records.get("Appointments",[]) if str(a.get("status","")).lower() in ("booked","confirmed","scheduled")]
        if not appts: st.info("No confirmed follow-up is recorded.")
        for a in appts:
            st.success("✓ Scheduled")
            st.markdown(f"**{pretty_date(a.get('appointment_at'))} · {local_time(a.get('appointment_at'))}**")
            st.caption(readable(a.get("reason")))
            if st.button("Edit Appointment",key="edit_"+str(a.get("appointment_id"))): edit_appointment(a)
with right:
    with st.container(border=True):
        st.subheader("Clinical Timeline")
        events=[]
        for c in records.get("Consultations",[]):
            ex=c.get("extracted") or {}
            if not isinstance(ex,dict): ex={}
            symptoms=ex.get("symptoms") or []
            meds=ex.get("medications") or []
            if isinstance(symptoms,list): symptoms=", ".join(str(x) for x in symptoms)
            events.append((str(c.get("created_at") or ""),"Consultation",ex.get("summary") or symptoms or "Clinical report saved",symptoms,meds))
        for a in records.get("Appointments",[]):
            events.append((str(a.get("appointment_at") or a.get("created_at") or ""),"Appointment · "+str(a.get("status") or "Recorded"),a.get("reason") or "Follow-up", "", []))
        events.sort(key=lambda x:x[0],reverse=True)
        if not events: st.info("No clinical events recorded.")
        else:
            html_events=[]
            for dt,kind,summary,symptoms,meds in events:
                medication_text="; ".join(readable(m) for m in meds) if isinstance(meds,list) else readable(meds)
                extra=(f"<p><b>Symptoms:</b> {esc(symptoms)}</p>" if symptoms else "")+(f"<p><b>Medications discussed:</b> {esc(medication_text)}</p>" if meds else "")
                html_events.append(f'<div class="timeline-event"><div class="timeline-date">{esc(pretty_date(dt))} · {esc(kind)}</div><p>{esc(summary)}</p>{extra}</div>')
            st.markdown('<div class="timeline">'+''.join(html_events)+'</div>',unsafe_allow_html=True)
        st.caption("Structured consultation events only. Raw audio transcripts are not displayed.")
