import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "women_safety.db"

st.set_page_config(
    page_title="SafeHer | Women Safety System",
    page_icon="🛡️",
    layout="wide",
)

# ---------- Database layer ----------
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trusted_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            contact_name TEXT NOT NULL,
            relationship TEXT,
            phone TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS safety_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT,
            location_text TEXT,
            status TEXT NOT NULL DEFAULT 'Logged',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS incident_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            location_text TEXT,
            urgency TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def password_digest(password, salt_hex):
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return digest.hex()


def create_user(full_name, email, password):
    salt_hex = secrets.token_hex(16)
    digest = password_digest(password, salt_hex)
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users(full_name,email,password_hash,password_salt,created_at) VALUES(?,?,?,?,?)",
                (full_name.strip(), email.strip().lower(), digest, salt_hex, now_text()),
            )
        return True, "Account created. Please sign in."
    except sqlite3.IntegrityError:
        return False, "An account with this email already exists."


def verify_user(email, password):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    if not row:
        return None
    candidate = password_digest(password, row["password_salt"])
    if hmac.compare_digest(candidate, row["password_hash"]):
        return {"id": row["id"], "full_name": row["full_name"], "email": row["email"]}
    return None


def add_contact(user_id, name, relationship, phone):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO trusted_contacts(user_id,contact_name,relationship,phone,created_at) VALUES(?,?,?,?,?)",
            (user_id, name.strip(), relationship.strip(), phone.strip(), now_text()),
        )


def get_contacts(user_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id,contact_name,relationship,phone,created_at FROM trusted_contacts WHERE user_id=? ORDER BY id DESC",
            (user_id,),
        ).fetchall()


def delete_contact(user_id, contact_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM trusted_contacts WHERE id=? AND user_id=?",
            (contact_id, user_id),
        )


def add_event(user_id, event_type, description, location_text, status="Logged"):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO safety_events(user_id,event_type,description,location_text,status,created_at) VALUES(?,?,?,?,?,?)",
            (user_id, event_type, description, location_text, status, now_text()),
        )


def get_events(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id,event_type,description,location_text,status,created_at FROM safety_events WHERE user_id=? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def add_incident(user_id, category, description, location_text, urgency):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO incident_reports(user_id,category,description,location_text,urgency,created_at) VALUES(?,?,?,?,?,?)",
            (user_id, category, description.strip(), location_text.strip(), urgency, now_text()),
        )
        conn.execute(
            "INSERT INTO safety_events(user_id,event_type,description,location_text,status,created_at) VALUES(?,?,?,?,?,?)",
            (user_id, "Incident report", f"{category}: {description.strip()}", location_text.strip(), "Reported", now_text()),
        )


def get_incidents(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id,category,description,location_text,urgency,created_at FROM incident_reports WHERE user_id=? ORDER BY id DESC",
            (user_id,),
        ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


init_db()

# ---------- UI helpers ----------
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1200px;}
.hero {padding: 1.3rem 1.5rem; border-radius: 16px; background: linear-gradient(120deg,#24133d,#713d75); color: white; margin-bottom: 1rem;}
.hero h1 {margin: 0; color: white; font-size: 2rem;}
.hero p {margin: .35rem 0 0 0; color: #f3eafa;}
.note {padding: .8rem 1rem; border-left: 4px solid #d97706; background: #fff7ed; border-radius: 6px; color: #7c2d12;}
.small-muted {color: #6b7280; font-size: .9rem;}
</style>
""", unsafe_allow_html=True)

def current_user():
    return st.session_state.get("user")


def show_auth():
    st.markdown('<div class="hero"><h1>🛡️ SafeHer</h1><p>Women Safety Alert & Incident Analytics System</p></div>', unsafe_allow_html=True)
    st.info("Create a demo account or sign in to manage trusted contacts, log SOS events, and review safety reports.")
    register_tab, login_tab = st.tabs(["Create account", "Sign in"])
    with register_tab:
        with st.form("register_form", clear_on_submit=False):
            name = st.text_input("Full name")
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password", help="Use a unique password for this demo.")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if not name.strip() or not email.strip() or not password:
                st.error("Please complete all required fields.")
            elif "@" not in email or "." not in email.split("@")[-1]:
                st.error("Please enter a valid email address.")
            elif len(password) < 8:
                st.error("Use a password with at least 8 characters.")
            elif password != confirm:
                st.error("The passwords do not match.")
            else:
                ok, message = create_user(name, email, password)
                if ok:
                    st.success(message)
                else:
                    st.error(message)
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email address", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign in", use_container_width=True)
        if submitted:
            user = verify_user(email, password)
            if user:
                st.session_state["user"] = user
                st.rerun()
            else:
                st.error("Email or password is incorrect.")


def metric_card(label, value, help_text=None):
    st.metric(label, value, help=help_text)


def main_app(user):
    st.sidebar.markdown("## 🛡️ SafeHer")
    st.sidebar.write(f"Signed in as **{user['full_name']}**")
    page = st.sidebar.radio(
        "Navigate",
        ["Dashboard", "SOS Alert", "Trusted Contacts", "Incident Reports", "Event History", "About & Safety"],
    )
    if st.sidebar.button("Sign out", use_container_width=True):
        st.session_state.pop("user", None)
        st.rerun()
    st.sidebar.caption("Software prototype • No real emergency messages are sent.")

    st.markdown(f'<div class="hero"><h1>Welcome, {user["full_name"].split()[0]} 👋</h1><p>Your personal safety workspace</p></div>', unsafe_allow_html=True)

    if page == "Dashboard":
        events = get_events(user["id"])
        incidents = get_incidents(user["id"])
        contacts = get_contacts(user["id"])
        total_events = len(events)
        sos_count = int((events["event_type"] == "SOS alert").sum()) if not events.empty else 0
        incident_count = len(incidents)
        c1, c2, c3 = st.columns(3)
        with c1: metric_card("Safety events", total_events)
        with c2: metric_card("SOS logs", sos_count)
        with c3: metric_card("Incident reports", incident_count)
        st.subheader("Quick actions")
        a, b = st.columns(2)
        with a:
            if st.button("🚨 Open SOS Alert", use_container_width=True):
                st.session_state["nav_to_sos"] = True
                st.info("Choose SOS Alert from the sidebar to continue.")
        with b:
            if st.button("📝 Report an incident", use_container_width=True):
                st.info("Choose Incident Reports from the sidebar to continue.")
        st.subheader("Recent activity")
        if events.empty:
            st.caption("No activity recorded yet. Use the SOS Alert or Incident Reports pages to add demo events.")
        else:
            st.dataframe(events.head(8), use_container_width=True, hide_index=True)
        st.markdown('<div class="note"><b>Prototype notice:</b> This app records events in a database. It does not contact police, emergency services, or trusted contacts.</div>', unsafe_allow_html=True)

    elif page == "SOS Alert":
        st.subheader("🚨 SOS Alert Simulator")
        st.write("Use this page to test how an SOS event is recorded. This prototype does not send SMS, calls, or live location.")
        with st.form("sos_form"):
            location = st.text_input("Current location (optional)", placeholder="e.g., College hostel, Chennai")
            details = st.text_area("Additional details (optional)", placeholder="What would you like to record?")
            confirm = st.checkbox("I understand this only records a demo event and does not contact emergency services.")
            submitted = st.form_submit_button("Record SOS event", type="primary", use_container_width=True)
        if submitted:
            if not confirm:
                st.error("Please confirm that you understand this is a demo-only event.")
            else:
                add_event(user["id"], "SOS alert", details or "SOS button activated in demo", location, "Demo only — not sent")
                st.success("SOS event recorded in your local database. No message or call was sent.")
                st.warning("If you are in immediate danger, contact local emergency services directly.")
        st.subheader("Trusted contacts")
        contacts = get_contacts(user["id"])
        if contacts:
            st.dataframe(pd.DataFrame([dict(c) for c in contacts])[["contact_name", "relationship", "phone"]], use_container_width=True, hide_index=True)
        else:
            st.caption("Add trusted contacts on the Trusted Contacts page. They are stored for reference only.")

    elif page == "Trusted Contacts":
        st.subheader("Trusted Contacts")
        st.write("Add people you may want to contact in a real emergency. This prototype stores their details but does not message them.")
        with st.form("contact_form", clear_on_submit=True):
            name = st.text_input("Contact name *")
            relationship = st.text_input("Relationship", placeholder="e.g., Parent, Friend")
            phone = st.text_input("Phone number *")
            submitted = st.form_submit_button("Add trusted contact", use_container_width=True)
        if submitted:
            digits = "".join(ch for ch in phone if ch.isdigit())
            if not name.strip() or len(digits) < 7:
                st.error("Enter a contact name and a valid phone number.")
            else:
                add_contact(user["id"], name, relationship, phone)
                st.success("Trusted contact added.")
                st.rerun()
        contacts = get_contacts(user["id"])
        if contacts:
            st.subheader("Saved contacts")
            for contact in contacts:
                cols = st.columns([3, 2, 2, 1])
                cols[0].write(f"**{contact['contact_name']}**")
                cols[1].write(contact["relationship"] or "—")
                cols[2].write(contact["phone"])
                if cols[3].button("Delete", key=f"del_{contact['id']}"):
                    delete_contact(user["id"], contact["id"])
                    st.rerun()
        else:
            st.caption("You haven't added any contacts yet.")

    elif page == "Incident Reports":
        st.subheader("📝 Incident Reports")
        with st.form("incident_form", clear_on_submit=True):
            category = st.selectbox("Incident category", ["Harassment", "Unsafe travel", "Suspicious activity", "Stalking", "Other"])
            description = st.text_area("Description *", placeholder="Describe what happened. Avoid including unnecessary sensitive details.")
            location = st.text_input("Location (optional)")
            urgency = st.selectbox("Urgency", ["Low", "Medium", "High"])
            submitted = st.form_submit_button("Save incident report", use_container_width=True)
        if submitted:
            if not description.strip():
                st.error("Please add a short description.")
            else:
                add_incident(user["id"], category, description, location, urgency)
                st.success("Incident report saved.")
                st.rerun()
        incidents = get_incidents(user["id"])
        if not incidents.empty:
            st.subheader("Your reports")
            st.dataframe(incidents, use_container_width=True, hide_index=True)
            st.download_button(
                "Download incident reports as CSV",
                incidents.to_csv(index=False).encode("utf-8"),
                file_name="my_incident_reports.csv",
                mime="text/csv",
            )
        else:
            st.caption("No incident reports have been saved yet.")

    elif page == "Event History":
        st.subheader("📊 Event History & Analytics")
        events = get_events(user["id"])
        if events.empty:
            st.info("No event history yet. Record a demo SOS event or add an incident report to see analytics.")
        else:
            events["created_at"] = pd.to_datetime(events["created_at"], errors="coerce")
            left, right = st.columns(2)
            with left:
                st.write("Events by type")
                st.bar_chart(events["event_type"].value_counts())
            with right:
                st.write("Events by status")
                st.bar_chart(events["status"].value_counts())
            st.write("Events over time")
            timeline = events.dropna(subset=["created_at"]).copy()
            if not timeline.empty:
                timeline["date"] = timeline["created_at"].dt.date.astype(str)
                counts = timeline.groupby("date").size().rename("events")
                st.line_chart(counts)
            st.dataframe(events, use_container_width=True, hide_index=True)
            st.download_button(
                "Download event history as CSV",
                events.to_csv(index=False).encode("utf-8"),
                file_name="my_safety_event_history.csv",
                mime="text/csv",
            )

    elif page == "About & Safety":
        st.subheader("About this project")
        st.write("SafeHer is a software-only prototype demonstrating a women-safety workflow using a web interface, Python logic, a SQLite database, and event analytics.")
        st.markdown("""
        **Current features**
        - Account registration and sign-in for a local demo
        - Trusted-contact management
        - SOS event simulation and event logging
        - Incident report form
        - Dashboard metrics and charts
        - CSV export of personal reports and event history
        """)
        st.markdown("""
        **Technology stack**
        - Frontend: Streamlit UI
        - Backend: Python application logic
        - Database: SQLite
        - Analytics: Pandas and Streamlit charts
        """)
        st.markdown('<div class="note"><b>Safety and privacy:</b> This is an academic prototype, not a verified emergency-response service. It does not send real alerts, track GPS, or contact authorities. Do not store highly sensitive details in a public demo. For real-world use, the system would need security testing, consent, reliable messaging/location integrations, and a response plan.</div>', unsafe_allow_html=True)

if current_user() is None:
    show_auth()
else:
    main_app(current_user())

st.markdown("---")
st.caption("SafeHer • Academic project prototype • Not for emergency use")