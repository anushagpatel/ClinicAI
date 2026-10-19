# ClinicAI Compact Doctor Workspace

Run `pip install -r requirements.txt` then `streamlit run app.py`.

Changes: compact homepage; hamburger navigation; patient records partial-name search; event timeline for a single matched patient; two-column patient profile with a scrollable timeline; edit patient and appointment dialogs. Raw consultation transcripts are not displayed in patient profiles. Follow-up is labeled scheduled only when a confirmed appointment record exists.

Screen heights vary. We deliberately **do not disable all browser scrolling**, since that would hide important content on smaller displays. Timeline scrolls within its own panel. Synthetic demo data only; do not use real patient information.

Configuration: copy `.env.example` to `.env`, configure AWS, never commit secrets. If `AWS_PROFILE` is empty, remove it from `.env` to avoid boto3 ProfileNotFound.
