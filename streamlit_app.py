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
FLASK_PORT = 5000
FLASK_URL  = f"http://localhost:{FLASK_PORT}"


# ── Start Flask in a background thread ──────────────────────
@st.cache_resource
def start_flask():
    """Starts Flask once and caches the thread."""
    # Import here so env vars are set first
    from app import app as flask_app

    def run():
        flask_app.run(
            host="0.0.0.0",
            port=FLASK_PORT,
            debug=False,
            use_reloader=False,
            threaded=True
        )

    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def wait_for_flask(timeout: int = 15) -> bool:
    """Poll Flask until it responds or timeout (seconds)."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(FLASK_URL, timeout=2)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


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
start_flask()

# ── Wait for Flask to be ready ───────────────────────────────
with st.spinner("🚀 Starting Voyager AI…"):
    ready = wait_for_flask(timeout=20)

if not ready:
    st.error("⚠️ Flask server didn't start in time. Please refresh the page.")
    st.stop()

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