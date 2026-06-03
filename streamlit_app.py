"""
╔══════════════════════════════════════════════════════════════╗
║  VOYAGER AI — streamlit_app.py                              ║
║  Streamlit Cloud deployment wrapper for the Flask app.      ║
║  This file starts the Flask server in a background thread   ║
║  and embeds it in a Streamlit iframe.                        ║
╚══════════════════════════════════════════════════════════════╝

HOW TO DEPLOY ON STREAMLIT CLOUD:
  1. Push your project to a GitHub repo with this structure:
       your-repo/
       ├── streamlit_app.py      ← this file (entry point)
       ├── app.py                ← your Flask app
       ├── requirements.txt      ← see below
       ├── .streamlit/
       │   └── config.toml       ← see below
       ├── templates/
       │   ├── login.html
       │   ├── index.html
       │   ├── dashboard.html
       │   ├── shared_trip.html
       │   └── email_itinerary.html
       ├── static/
       │   ├── style.css
       │   └── script.js
       └── data/                 ← optional fallback JSON files

  2. Go to https://share.streamlit.io → New app
     → Select your repo → Main file: streamlit_app.py

  3. Add secrets in Streamlit Cloud dashboard (Settings → Secrets):
       SECRET_KEY = "your-secret-key"
       ANTHROPIC_API_KEY = "sk-ant-..."
       MAIL_SERVER = "smtp.gmail.com"
       MAIL_PORT = "587"
       MAIL_USE_TLS = "True"
       MAIL_USERNAME = "you@gmail.com"
       MAIL_PASSWORD = "your-app-password"
       MAIL_DEFAULT_SENDER = "you@gmail.com"

REQUIREMENTS.TXT content:
  streamlit>=1.32.0
  flask>=3.0.0
  flask-sqlalchemy>=3.1.0
  flask-bcrypt>=1.0.1
  flask-mail>=0.10.0
  flask-limiter>=3.5.0
  anthropic>=0.25.0
  python-dotenv>=1.0.0

.streamlit/config.toml content:
  [server]
  headless = true
  port = 8501

  [theme]
  primaryColor = "#C9853A"
  backgroundColor = "#F5F0E8"
  secondaryBackgroundColor = "#EDE7D9"
  textColor = "#1A1A2E"
"""

import streamlit as st
import threading
import time
import os
import requests

# ── Pull secrets into environment variables ──────────────────
# Streamlit Cloud stores secrets in st.secrets, but Flask reads
# from os.environ, so we sync them here before importing app.py

_SECRET_KEYS = [
    "SECRET_KEY", "ANTHROPIC_API_KEY",
    "MAIL_SERVER", "MAIL_PORT", "MAIL_USE_TLS",
    "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_DEFAULT_SENDER"
]

for key in _SECRET_KEYS:
    if key in st.secrets:
        os.environ[key] = str(st.secrets[key])

# ── Flask port ───────────────────────────────────────────────
# Port used for local testing (optional)
FLASK_PORT = 5000
# Public Flask URL – set FLASK_PUBLIC_URL in Streamlit secrets for deployed environments.
# Falls back to localhost for local development.
FLASK_URL = os.getenv("FLASK_PUBLIC_URL", f"http://localhost:{FLASK_PORT}")


# ── Start Flask in a background thread ──────────────────────
// Removed embedded Flask server start – the Flask app should be hosted separately.
// The background thread is no longer needed when FLASK_URL points to an external service.


// Removed wait_for_flask – not needed when embedding an external Flask URL.


# ── Streamlit page config ────────────────────────────────────
st.set_page_config(
    page_title="Voyager AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Hide Streamlit chrome so the iframe fills the page ───────
st.markdown("""
<style>
  /* Hide Streamlit header, footer, and padding */
  #MainMenu, header, footer { display: none !important; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  .stApp { overflow: hidden; }
  iframe { border: none; display: block; }
</style>
""", unsafe_allow_html=True)

# ── Start Flask ──────────────────────────────────────────────
// No need to start or wait for Flask – assume FLASK_URL is reachable.
with st.spinner("🚀 Loading Voyager AI…"):
    # Optionally, you could probe the URL here, but Streamlit Cloud will load the iframe directly.
    pass

# ── Embed Flask via iframe ───────────────────────────────────
st.markdown(
    f"""
    <iframe
      src="{FLASK_URL}"
      width="100%"
      height="100vh"
      style="height:100vh;width:100%;border:none;display:block;"
      allowfullscreen
    ></iframe>
    """,
    unsafe_allow_html=True
)

# ── Keep Streamlit alive ─────────────────────────────────────
# Streamlit re-runs on interaction; this dummy placeholder
# prevents the script from ending and killing the thread.
st.markdown(
    "<style>div[data-testid='stVerticalBlock']>div:last-child{display:none}</style>",
    unsafe_allow_html=True
)
time.sleep(1)