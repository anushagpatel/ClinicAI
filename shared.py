"""CareNote - Local clinical assistant demo. Synthetic data only."""

import asyncio
import json
import os
import uuid
from datetime import datetime
import boto3
from decimal import Decimal
from textwrap import dedent

import streamlit as st

import database as db
from agents import build_graph
from aws_services import transcribe_audio
from fastmcp import Client
from mcp_server import mcp


# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------

defaults = {
    "page": "Home",
    "transcript": "",
    "pending_report": None,
    "pending_patient_id": "",
    "saved_record": None,
    "show_saved_popup": False,
    "lookup_patient_id": "",
    "lookup_result": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------------------------
# HELPERS
# ---------------------------------------------------

def json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def report_json(data):
    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        default=json_default,
    )


async def save_via_mcp(patient_id, report, transcript, reviewer):
    async with Client(mcp) as client:
        response = await client.call_tool(
            "save_reviewed_consultation",
            {
                "patient_id": patient_id,
                "extracted_json": report_json(report),
                "transcript": transcript,
                "approved_by": reviewer,
            },
        )

        if getattr(response, "is_error", False):
            raise RuntimeError(str(response.content))

        return response


def load_patient(patient_id):
    patient = db.get("Patients", patient_id)

    if not patient:
        return None

    consultations = [
        item
        for item in db.list_items("Consultations", limit=500)
        if item.get("patient_id") == patient_id
    ]

    return patient, consultations


# ---------------------------------------------------
# SUCCESS POPUP
# ---------------------------------------------------

def appointment_details(extraction):
    raw = (extraction.get("appointment") or
           extraction.get("next_appointment") or
           extraction.get("appointment_request") or
           extraction.get("follow_up") or {})
    if isinstance(raw, list):
        raw = raw[0] if raw else {}
    if isinstance(raw, str):
        return {"reason": raw}
    return raw if isinstance(raw, dict) else {}


def parse_appointment_time(date_text, time_text):
    """Accept 10:00 AM, 10:00AM, 2:30 PM, or legacy 14:30."""
    from datetime import datetime
    clean = " ".join(str(time_text).strip().upper().replace(".", "").split())
    clean = __import__("re").sub(r"\s*(AM|PM)$", r" \1", clean).strip()
    for fmt in ("%I:%M %p", "%I %p", "%H:%M"):
        try:
            return datetime.strptime(f"{date_text.strip()} {clean}", "%Y-%m-%d " + fmt)
        except ValueError:
            continue
    raise ValueError("Enter appointment time as 10:00 AM or 2:30 PM.")


def display_appointment_time(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(str(value)).strftime("%I:%M %p").lstrip("0")
    except ValueError:
        pass
    try:
        return parse_appointment_time("2026-01-01", str(value)).strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return str(value)


def conversation_confirms_appointment(transcript):
    """Detect explicit booking language, not just a request for a preferred slot."""
    import re
    text = str(transcript or "").lower()
    patterns = (
        r"(?:appointment|visit|slot)\s+(?:is|has been|was)\s+(?:confirmed|booked|scheduled)",
        r"(?:i|we)(?:'ve| have)?\s+(?:confirmed|booked|scheduled)\s+(?:your|the|an)\s+(?:appointment|visit|slot)",
        r"(?:your|the)\s+(?:appointment|visit|slot)\s+(?:has been\s+)?confirmed",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def book_appointment(patient_id, date_text, time_text, reason, clinician):
    from zoneinfo import ZoneInfo
    when = parse_appointment_time(date_text, time_text)
    aware = when.replace(tzinfo=ZoneInfo("America/New_York"))
    return db.book_appointment(patient_id, aware.isoformat(), clinician, "Clinician confirmed", reason)


@st.dialog("Generated Consultation Report", width="large", dismissible=False)
def display_consultation_report():
    result = st.session_state.get("pending_report")
    if not result:
        return
    extraction = result.get("extraction") or {}
    appt = appointment_details(extraction)

    with st.container(border=True):
        st.subheader("Generated Consultation Report")
        with st.form("consultation_save_form"):
            patient_name = st.text_input(
                "Patient Name", value=str(extraction.get("patient_name") or "")
            )
            dob_text = st.text_input(
                "Date of Birth (YYYY-MM-DD)",
                value=str(extraction.get("date_of_birth") or extraction.get("dob") or "")
            )
            age_value = extraction.get("age")
            age_text = st.text_input(
                "Age", value=str(age_value) if age_value is not None else ""
            )
            st.markdown("**Consultation Summary**")
            st.write(extraction.get("summary") or "Not recorded")
            st.markdown("**Symptoms**")
            symptoms = extraction.get("symptoms") or []
            st.write(", ".join(map(str, symptoms)) if isinstance(symptoms, list) else str(symptoms))
            st.markdown("**Medications Discussed**")
            for med in extraction.get("medications") or []:
                if isinstance(med, dict):
                    st.write(f"• {med.get('name', 'Not specified')} — {med.get('dosage') or 'Dose not stated'}")
                else:
                    st.write(str(med))

            st.markdown("#### Appointment Booking")
            date_text = st.text_input(
                "Appointment Date (YYYY-MM-DD)",
                value=str(appt.get("date") or appt.get("appointment_date") or ""),
            )
            time_text = st.text_input(
                "Appointment Time (12-hour, e.g. 10:00 AM)",
                value=display_appointment_time(appt.get("time") or appt.get("appointment_time") or ""),
            )
            reason = st.text_input(
                "Reason", value=str(appt.get("reason") or "Follow-up consultation")
            )
            clinician = st.text_input("Clinician for appointment", value=str(appt.get("clinician") or ""))
            st.caption("Only book a slot that your clinic has independently confirmed as available.")
            explicit_confirmation = conversation_confirms_appointment(st.session_state.get("transcript", ""))
            if explicit_confirmation:
                st.info("The conversation mentions a confirmed appointment. Verify the slot before saving it to your schedule.")
            book_requested = st.checkbox(
                "Book this appointment in my schedule",
                value=explicit_confirmation and bool(date_text and time_text and clinician),
                help="Only select after verifying the slot is available. A spoken request alone does not create a booking.",
            )
            submitted = st.form_submit_button(
                "Save Patient Record & Continue", type="primary", use_container_width=True
            )

        if submitted:
            try:
                if not patient_name.strip():
                    raise ValueError("Patient name is required.")
                age = int(age_text) if age_text.strip() else None
                if age is not None and not 0 <= age <= 120:
                    raise ValueError("Enter a valid age.")
                if book_requested:
                    if not date_text.strip() or not time_text.strip():
                        raise ValueError("Enter an appointment date and time.")
                    parse_appointment_time(date_text, time_text)
                corrected = dict(extraction)
                if dob_text.strip():
                    from datetime import date
                    corrected["date_of_birth"] = date.fromisoformat(dob_text.strip()).isoformat()
                corrected.update({"patient_name": patient_name.strip(), "age": age})
                if date_text.strip() or time_text.strip():
                    corrected["appointment"] = {
                        "date": date_text.strip(), "time": time_text.strip(),
                        "reason": reason.strip(), "clinician": clinician.strip(),
                        "requested": True, "confirmed_in_conversation": explicit_confirmation
                    }
                existing_id = st.session_state.get("pending_patient_id") or ""
                dob_value = corrected.get("date_of_birth") or corrected.get("dob")
                if not existing_id and dob_value:
                    exact = db.search_patients(patient_name.strip(), str(dob_value))
                    if len(exact) == 1:
                        existing_id = exact[0]["patient_id"]
                    elif len(exact) > 1:
                        raise ValueError("Multiple matching patient records. Open the correct patient record first.")
                with st.spinner("Saving patient record..."):
                    if existing_id:
                        if not db.get("Patients", existing_id):
                            raise ValueError("Existing patient not found.")
                        patient_id = existing_id
                    else:
                        patient = db.create_patient(
                            patient_name.strip(), age,
                            dob=corrected.get("date_of_birth") or corrected.get("dob"),
                            insurance_company=corrected.get("insurance_company"),
                            insurance_member_id=corrected.get("insurance_member_id") or corrected.get("insurance_number"),
                            phone=corrected.get("phone"), email=corrected.get("email"),
                        )
                        patient_id = patient["patient_id"]
                    db.update_patient_details(
                        patient_id,
                        dob=corrected.get("date_of_birth") or corrected.get("dob"),
                        insurance_company=corrected.get("insurance_company"),
                        insurance_member_id=corrected.get("insurance_member_id") or corrected.get("insurance_number"),
                        phone=corrected.get("phone"), email=corrected.get("email"),
                    )
                    asyncio.run(save_via_mcp(
                        patient_id, corrected, st.session_state.transcript,
                        "Clinical assistant demo"
                    ))
                st.session_state.saved_record = patient_id
                st.session_state.pending_report = None
                st.session_state["report_save_message"] = "Patient record saved successfully."
                if book_requested:
                    try:
                        appointment_id = book_appointment(
                            patient_id, date_text.strip(), time_text.strip(), reason.strip(), clinician.strip()
                        )
                        st.session_state["report_save_message"] += f" Appointment booked. Reference: {appointment_id['appointment_id']}"
                    except Exception as booking_error:
                        st.session_state["report_save_message"] += f" Appointment was not booked: {booking_error}"
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to save consultation: {exc}")


# ---------------------------------------------------
# PATIENT RECORDS - VIEW AND EDIT
# ---------------------------------------------------

def show_patient_record(patient, consultations):
    patient_id = patient["patient_id"]

    st.subheader(patient.get("name") or "Patient")
    st.caption("Patient profile and consultation history")

    with st.expander("Edit patient profile"):
        with st.form(f"edit_patient_{patient_id}"):
            name = st.text_input(
                "Full Name",
                value=patient.get("name") or "",
            )

            age = st.text_input(
                "Age",
                value=(
                    str(patient["age"])
                    if patient.get("age") is not None
                    else ""
                ),
            )

            save_profile = st.form_submit_button(
                "Save Profile Changes",
                type="primary",
            )

        if save_profile:
            try:
                age_number = int(age) if age.strip() else None

                db.update_patient(
                    patient_id,
                    name,
                    age_number,
                )

                st.session_state.lookup_result = load_patient(
                    patient_id
                )

                st.success("Patient profile updated.")
                st.rerun()

            except Exception as exc:
                st.error(f"Unable to update profile: {exc}")

    st.divider()
    st.subheader("Consultation History")

    if not consultations:
        st.info("No consultations saved for this patient.")
        return

    consultations = sorted(
        consultations,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )

    for consultation in consultations:
        consultation_id = consultation["consultation_id"]
        created = consultation.get("created_at", "")[:10]
        extracted = consultation.get("extracted") or {}

        with st.expander(
            f"Consultation | {created} | {consultation_id}"
        ):
            st.markdown("**Consultation Summary**")
            st.write(extracted.get("summary") or "Not discussed")

            st.markdown("**Symptoms**")
            st.write(
                ", ".join(extracted.get("symptoms") or [])
                or "Not discussed"
            )

            st.markdown("**Medications Discussed**")

            medications = extracted.get("medications") or []

            if medications:
                for medication in medications:
                    if isinstance(medication, dict):
                        st.write(
                            f"• {medication.get('name') or 'Unspecified'}"
                            f" — {medication.get('dosage') or 'Dose not stated'}"
                        )
                    else:
                        st.write(str(medication))
            else:
                st.write("Not discussed")

            st.markdown("**Follow-up**")

            follow = extracted.get("follow_up") or {}

            if follow.get("requested"):
                st.write(
                    " | ".join(
                        str(follow[key])
                        for key in ("date", "time", "clinician")
                        if follow.get(key)
                    )
                    or "Follow-up requested; details not specified"
                )
                st.caption("Appointment not automatically booked.")
            else:
                st.write("Not discussed")

            st.caption(
                f"Originally reviewed by: "
                f"{consultation.get('approved_by') or 'Unknown'}"
            )

            with st.expander("Original Transcript"):
                st.text(consultation.get("transcript") or "")

            with st.expander("Edit Consultation Report"):
                with st.form(f"edit_consultation_{consultation_id}"):
                    corrected_text = st.text_area(
                        "Edit Report",
                        value=report_json(extracted),
                        height=320,
                    )

                    editor = st.text_input(
                        "Edited by",
                        key=f"editor_{consultation_id}",
                    )

                    confirmed = st.checkbox(
                        "I have reviewed these corrections.",
                        key=f"confirmed_{consultation_id}",
                    )

                    save_changes = st.form_submit_button(
                        "Save Changes",
                        type="primary",
                    )

                if save_changes:
                    try:
                        if not confirmed:
                            raise ValueError(
                                "Confirm that you reviewed the changes."
                            )

                        if not editor.strip():
                            raise ValueError(
                                "Enter the reviewing clinician's name."
                            )

                        corrected = json.loads(corrected_text)

                        if not isinstance(corrected, dict):
                            raise ValueError(
                                "Report must be a JSON object."
                            )

                        db.update_consultation(
                            consultation_id,
                            corrected,
                            editor.strip(),
                        )

                        st.session_state.lookup_result = load_patient(
                            patient_id
                        )

                        st.success("Consultation updated.")
                        st.rerun()

                    except Exception as exc:
                        st.error(f"Unable to save changes: {exc}")


