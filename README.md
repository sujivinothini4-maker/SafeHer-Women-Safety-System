# SafeHer — Women Safety Alert & Incident Analytics System

SafeHer is a **software-only academic prototype** for a women-safety workflow. It combines a Streamlit frontend, Python application logic, a SQLite database, and basic analytics. No hardware is required for this version.

## Features

- Account registration and sign-in (passwords are salted and hashed)
- Add and delete trusted contacts
- Simulate and record SOS events
- Create incident reports with category, location, and urgency
- View event history and dashboard metrics
- Visualize event types, statuses, and event counts over time
- Export incident reports and event history as CSV

## Technology stack

- Python
- Streamlit (web UI)
- SQLite (database)
- Pandas (data handling and analytics)

## Project structure

```text
Women_Safety_Alert_System/
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

The SQLite database (`women_safety.db`) is created automatically when the app first runs. It is excluded from Git by `.gitignore`.

## Run locally

1. Install Python 3.10 or newer.
2. Open a terminal in this project folder.
3. Install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   python -m streamlit run app.py
   ```

5. Open the local URL shown in the terminal, usually `http://localhost:8501`.
6. Create a demo account and sign in.

## Deploy on Streamlit Community Cloud

1. Upload `app.py`, `requirements.txt`, `README.md`, and `.gitignore` to a public GitHub repository.
2. In Streamlit Community Cloud, create an app from that repository.
3. Set the main file path to `app.py`.
4. Deploy.

**Important:** Streamlit Community Cloud's local filesystem is not a dependable persistent database for production. The SQLite database is suitable for a local demo; for a deployed multi-user app, use a managed database and configure access controls.

## Limitations and safety notice

This is a demonstration project. The SOS action **only records an event in the database**. It does not send SMS, place calls, share GPS coordinates, or contact police or emergency services. It must not be represented as a real emergency-response service.

Before real-world use, the project would need a reliable alert provider, explicit consent, secure data handling, access-control review, abuse testing, and a clear emergency-response plan. Do not enter sensitive personal information into a public demo.

## Suggested future enhancements

- Connect an SMS provider for opt-in alert delivery
- Add consent-based location sharing
- Move from SQLite to a managed database for hosted deployment
- Add audit logs, rate limiting, and account recovery
- Add optional map visualizations after privacy and consent requirements are addressed
