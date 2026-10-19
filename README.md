# ClinicAI — Voice-First Clinical Assistant

ClinicAI is a doctor-focused application that converts recorded patient consultations into structured clinical records using AWS and Generative AI. It helps doctors document visits, maintain patient histories, and manage follow-up appointments without manually entering every detail.

The application uses Amazon Transcribe for speech-to-text conversion, Amazon Nova through Amazon Bedrock for clinical information extraction, and DynamoDB for storing patient records. LangGraph manages the processing workflow, while MCP tools handle database operations.

This project was developed as a prototype to explore how voice-based AI systems can reduce repetitive clinical documentation work.

## Problem Statement

Clinical documentation takes time during and after patient consultations. Doctors need to record symptoms, medications, patient history, and follow-up instructions while maintaining accurate records across multiple visits.

Manually entering this information can interrupt patient interactions and create additional administrative work.

ClinicAI addresses this by capturing consultation audio and generating structured reports that doctors can review before saving. Previous records are available through a searchable patient profile, reducing the need to manually navigate through individual consultation notes.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python |
| Frontend | Streamlit |
| Cloud Platform | AWS |
| Speech-to-Text | Amazon Transcribe |
| Generative AI | Amazon Bedrock, Amazon Nova Micro |
| AI Workflow | LangGraph |
| Tool Integration | MCP, FastMCP |
| Database | Amazon DynamoDB |
| Audio Storage | Amazon S3 |
| AWS Integration | Boto3 |
| Configuration | python-dotenv |

## Features

### Voice-Based Consultation

Doctors can record patient conversations directly from the application. Audio is uploaded to Amazon S3 and processed by Amazon Transcribe to generate a text transcript.

The transcript can be reviewed and corrected before generating the clinical report.

### AI-Generated Consultation Reports

Amazon Nova extracts relevant information from the conversation, including:

- Patient name, age, and date of birth
- Contact and insurance information
- Reported symptoms
- Medications discussed
- Consultation summary
- Follow-up appointment details

The extracted information is presented in an editable report popup. The doctor reviews the report before saving it to the database.

### Patient Records

Patient information is stored in DynamoDB and can be accessed through the Patient Records page.

The application supports partial-name searches and displays matching patient profiles. Each profile contains patient details, previous consultation summaries, medication information, and follow-up appointments.

### Clinical Timeline

Patient profiles include a timeline of previous consultation events. This allows doctors to review earlier visits, reported symptoms, and follow-up plans in chronological order.

The timeline displays structured clinical information rather than full conversation transcripts.

### Appointment Management

Follow-up dates and times mentioned during consultations are extracted and displayed in a readable format.

Doctors can review appointment details, save confirmed bookings, and edit or reschedule appointments from the patient profile.

Requested appointments and confirmed bookings are handled separately.

## System Architecture

```text
Doctor–Patient Conversation
          |
          v
    Streamlit UI
          |
          v
    Audio Recording
          |
          v
      Amazon S3
          |
          v
   Amazon Transcribe
          |
          v
    Text Transcript
          |
          v
  LangGraph Workflow
          |
          v
 Amazon Bedrock (Nova)
          |
          v
 Structured Clinical Data
          |
          v
     Doctor Review
          |
          v
     MCP / FastMCP
          |
          v
    Amazon DynamoDB
          |
          v
 Patient Records / Timeline / Appointments
```

### Workflow

1. The doctor records a consultation using the Streamlit interface.
2. The recorded audio is temporarily stored in Amazon S3.
3. Amazon Transcribe converts the audio into text.
4. LangGraph coordinates the extraction and validation workflow.
5. Amazon Nova processes the transcript and extracts structured information.
6. The doctor reviews and edits the generated report.
7. MCP tools save the approved data to DynamoDB.
8. The saved information becomes available through patient profiles and consultation histories.

## Database

The application uses three DynamoDB tables:

| Table | Data Stored |
|---|---|
| ClinicalDemoPatients | Patient demographics and profile information |
| ClinicalDemoConsultations | Consultation reports and clinical history |
| ClinicalDemoAppointments | Follow-up appointment records |

## Potential Impact

The primary goal is to reduce the time doctors spend on repetitive documentation.

For example, consider a clinic where a doctor handles 20 consultations per day. If automated documentation saves an average of three minutes per consultation, the doctor could recover approximately one hour per working day.

Using a hypothetical value of $100 per hour of clinician time:

| Metric | Estimate |
|---|---:|
| Consultations per day | 20 |
| Time saved per consultation | 3 minutes |
| Time saved per day | 1 hour |
| Working days per year | 220 |
| Annual time saved per doctor | 220 hours |
| Annual value of time saved per doctor | $22,000 |
| Potential annual value for 5 doctors | $110,000 |

These figures are illustrative estimates, not measured results from the application. Actual savings would depend on documentation accuracy, review time, usage, operational costs, and clinical workflow integration.

In addition to time savings, the application aims to make patient information easier to retrieve and follow-up records easier to manage.

## Running the Project

### Prerequisites

- Python
- AWS account with the required service permissions
- AWS CLI configured locally
- Access to Amazon Bedrock and the configured Nova model
- An S3 bucket for audio processing
- DynamoDB tables for patient records

### Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/ClinicAI.git
cd ClinicAI
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project directory:

```env
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=amazon.nova-micro-v1:0
S3_BUCKET=your-bucket-name
DDB_PREFIX=ClinicalDemo
TRANSCRIBE_LANGUAGE=en-US
```

Verify AWS credentials:

```bash
aws sts get-caller-identity
```

Run the application:

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`.

## Challenges

Some of the main challenges during development included:

- Integrating Amazon Transcribe with S3 for audio processing.
- Handling AWS credentials and service permissions.
- Extracting consistent structured information from unstructured conversations.
- Coordinating extraction, validation, and database operations through LangGraph.
- Maintaining patient records across multiple consultations.
- Distinguishing appointment requests from confirmed bookings.
- Designing a compact interface that presents clinical information without excessive scrolling.

## Future Improvements

- Real-time streaming transcription instead of processing recorded audio after the consultation.
- Doctor authentication and role-based access.
- Integration with external scheduling systems.
- Integration with existing electronic health record systems.
- Improved patient matching and duplicate detection.
- Clinical terminology validation.
- Audit logging and record versioning.
- Evaluation of transcription accuracy, extraction quality, and documentation time savings.

## Project Status

ClinicAI is a functional prototype intended for development and demonstration using synthetic patient data. It is not intended for use with real patient records or as a replacement for a production EHR system.

AI-generated clinical information requires human review. Production deployment would require additional security, privacy, and healthcare compliance controls.
