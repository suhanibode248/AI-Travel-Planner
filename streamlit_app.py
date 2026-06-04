import streamlit as st
import uuid
import json
from dotenv import load_dotenv
import os

load_dotenv()

# ── Pull secrets from Streamlit Cloud ──────────────────────────
try:
    for key in ["OPENROUTER_API_KEY","MAIL_SERVER","MAIL_PORT","MAIL_USE_TLS",
                "MAIL_USERNAME","MAIL_PASSWORD","MAIL_DEFAULT_SENDER"]:
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])
except Exception:
    pass

from db import init_db, get_db, User, SavedTrip, hash_password, check_password
from ai_service import generate_with_ai, generate_static_fallback
from email_service import send_itinerary_email

st.set_page_config(page_title="Voyager AI", page_icon="✈️", layout="wide",
                   initial_sidebar_state="collapsed")

init_db()

# ── Session State ───────────────────────────────────────────────
for k, v in [("user_id", None), ("view", "login"), ("name", ""),
             ("current_plan", None), ("current_plan_meta", None),
             ("auth_tab", "login")]:
    if k not in st.session_state:
        st.session_state[k] = v

def go_to(view_name):
    st.session_state.view = view_name
    st.rerun()

# ═══════════════════════════════════════════════════════════════
#  GLOBAL CSS
# ═══════════════════════════════════════════════════════════════
def inject_css():
    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
/* ── Reset Streamlit chrome ── */
#MainMenu, header, footer { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none; }
div[data-testid="stDecoration"] { display: none; }

:root {
  --sand:#F5F0E8; --sand2:#EDE7D9;
  --dark:#0D1117; --dark2:#161B24;
  --card:#ffffff;
  --amber:#C9853A; --amber-l:#E8A85A; --amber-p:rgba(201,133,58,.12);
  --text:#1A1A2E; --muted:#6B7280;
  --border:#E0D9CD;
  --success:#1D9E75; --danger:#E23744;
  --r-sm:8px; --r-md:12px; --r-lg:18px; --r-xl:24px;
  --sh-sm:0 1px 4px rgba(0,0,0,.06);
  --sh-md:0 4px 20px rgba(0,0,0,.08);
  --sh-lg:0 12px 48px rgba(0,0,0,.12);
  --tr:0.2s cubic-bezier(.4,0,.2,1);
}

body, .stApp {
  background: var(--sand) !important;
  font-family:'DM Sans', system-ui, sans-serif;
  color: var(--text);
}

/* ── Animations ── */
@keyframes fadeUp   { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:none} }
@keyframes spin     { to{transform:rotate(360deg)} }
@keyframes shimmer  { 0%,100%{opacity:.4} 50%{opacity:.9} }
@keyframes pop      { from{opacity:0;transform:scale(.92)} to{opacity:1;transform:none} }

/* ── Scrollbar ── */
::-webkit-scrollbar      { width:6px; }
::-webkit-scrollbar-track{ background:var(--sand2); }
::-webkit-scrollbar-thumb{ background:var(--border); border-radius:3px; }

/* ── Toast ── */
.toast {
  position:fixed; bottom:24px; left:50%;
  transform:translateX(-50%) translateY(80px);
  background:var(--text); color:#fff;
  padding:12px 24px; border-radius:30px;
  font-size:14px; font-weight:500;
  transition:transform .4s cubic-bezier(.34,1.56,.64,1);
  z-index:9999; pointer-events:none; white-space:nowrap;
}
.toast.show    { transform:translateX(-50%) translateY(0); }
.toast.success { background:var(--success); }
.toast.error   { background:var(--danger); }

/* ── NAV ── */
.vg-nav {
  position:sticky; top:0; z-index:100;
  background:var(--sand); border-bottom:1px solid var(--border);
  backdrop-filter:blur(8px);
}
.vg-nav-inner {
  max-width:1100px; margin:0 auto; padding:0 24px; height:58px;
  display:flex; align-items:center; justify-content:space-between;
}
.vg-logo {
  font-family:'Playfair Display',serif; font-size:22px; color:var(--text);
  display:flex; align-items:center; gap:8px; cursor:pointer;
}
.vg-dot { width:8px;height:8px;border-radius:50%;background:var(--amber);display:inline-block; }
.vg-nav-links { display:flex; align-items:center; gap:8px; }
.vg-nav-btn {
  padding:7px 14px; font-family:'DM Sans',sans-serif; font-size:13px;
  background:transparent; border:1px solid var(--border); border-radius:var(--r-sm);
  color:var(--muted); cursor:pointer; transition:all var(--tr);
  text-decoration:none;
}
.vg-nav-btn:hover { border-color:var(--amber); color:var(--amber); }
.vg-nav-btn.primary {
  background:var(--text); border-color:var(--text); color:#fff;
}
.vg-nav-btn.primary:hover { background:var(--amber); border-color:var(--amber); }
.vg-nav-user { font-size:13px; font-weight:500; color:var(--text); padding:0 4px; }

/* ── LOGIN PAGE ── */
.login-grid {
  display:grid; grid-template-columns:1fr 1fr;
  min-height:100vh;
}
@media(max-width:768px){ .login-grid{grid-template-columns:1fr;} .vp{display:none!important;} }

/* Visual panel */
.vp {
  position:relative; overflow:hidden;
  background:var(--dark); min-height:100vh;
}
.vp-bg {
  position:absolute; inset:0;
  background:
    radial-gradient(ellipse at 30% 70%,rgba(201,133,58,.35) 0%,transparent 60%),
    radial-gradient(ellipse at 80% 20%,rgba(201,133,58,.15) 0%,transparent 50%);
  z-index:1;
}
.dest-grid {
  position:absolute; inset:0;
  display:grid; grid-template-columns:1fr 1fr;
  grid-template-rows:1fr 1fr 1fr; gap:3px;
  opacity:.55; z-index:0;
}
.dest-tile {
  display:flex; align-items:flex-end; padding:12px;
  font-size:11px; color:rgba(255,255,255,.45);
  letter-spacing:.08em; text-transform:uppercase;
  animation:shimmer 6s ease-in-out infinite;
}
.dest-tile:nth-child(1){background:#1c2537;animation-delay:0s;}
.dest-tile:nth-child(2){background:#1a2420;animation-delay:.5s;}
.dest-tile:nth-child(3){background:#221c1a;animation-delay:1s;}
.dest-tile:nth-child(4){background:#1a1e2a;animation-delay:1.5s;}
.dest-tile:nth-child(5){background:#20251a;animation-delay:2s;}
.dest-tile:nth-child(6){background:#1e1a24;animation-delay:2.5s;}

.vp-content {
  position:absolute; inset:0; z-index:2;
  display:flex; flex-direction:column;
  justify-content:flex-end; padding:48px 40px;
}
.vp-tag {
  display:inline-flex; align-items:center; gap:8px;
  background:rgba(201,133,58,.2); border:1px solid rgba(201,133,58,.4);
  color:var(--amber-l); font-size:11px; letter-spacing:.12em;
  text-transform:uppercase; padding:6px 14px; border-radius:20px;
  margin-bottom:20px; width:fit-content;
}
.vp-headline {
  font-family:'Playfair Display',serif;
  font-size:42px; font-weight:700; color:#fff; line-height:1.15; margin-bottom:16px;
}
.vp-headline em { color:var(--amber-l); font-style:italic; }
.vp-sub { font-size:14px; color:rgba(255,255,255,.5); line-height:1.7; max-width:300px; }
.vp-stats {
  display:flex; gap:32px; margin-top:32px; padding-top:24px;
  border-top:1px solid rgba(255,255,255,.1);
}
.vp-stat-num { font-family:'Playfair Display',serif; font-size:22px; color:var(--amber-l); font-weight:700; }
.vp-stat-lbl { font-size:11px; color:rgba(255,255,255,.4); letter-spacing:.06em; text-transform:uppercase; margin-top:2px; }

/* Form panel */
.fp {
  display:flex; flex-direction:column; justify-content:center; align-items:center;
  padding:48px 56px; background:var(--sand); animation:fadeUp .6s ease both;
}
@media(max-width:768px){ .fp{padding:32px 24px;} }
.fp-inner { width:100%; max-width:360px; }
.fp-logo { font-family:'Playfair Display',serif; font-size:26px; color:var(--text); margin-bottom:6px; display:flex; align-items:center; gap:10px; }
.fp-sub { font-size:13px; color:var(--muted); margin-bottom:28px; }

.auth-tabs {
  display:flex; margin-bottom:28px;
  border:1.5px solid var(--border); border-radius:10px; overflow:hidden;
}
.auth-tab {
  flex:1; padding:10px; font-family:'DM Sans',sans-serif;
  font-size:13px; font-weight:500; cursor:pointer; border:none;
  background:transparent; color:var(--muted); transition:all .2s;
}
.auth-tab.active { background:var(--text); color:#fff; }

/* ── Shared Form Styles ── */
.vg-label {
  display:block; font-size:11px; font-weight:500;
  letter-spacing:.08em; text-transform:uppercase; color:var(--text);
  opacity:.65; margin-bottom:6px;
}
.vg-field { margin-bottom:16px; }
.vg-input-wrap { position:relative; }
.vg-icon { position:absolute; left:14px; top:50%; transform:translateY(-50%); font-size:16px; pointer-events:none; }

/* Override Streamlit inputs */
div[data-testid="stTextInput"] > div > div > input,
div[data-testid="stNumberInput"] > div > div > input {
  padding-left: 14px !important;
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  background: #fff !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 14px !important;
  color: var(--text) !important;
  transition: border-color var(--tr), box-shadow var(--tr);
}
div[data-testid="stTextInput"] > div > div > input:focus,
div[data-testid="stNumberInput"] > div > div > input:focus {
  border-color: var(--amber) !important;
  box-shadow: 0 0 0 4px rgba(201,133,58,.12) !important;
}
div[data-testid="stSelectbox"] > div > div {
  border: 1.5px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  background: #fff !important;
}

/* Override Streamlit buttons */
div[data-testid="stForm"] button[kind="primaryFormSubmit"],
button[data-testid="baseButton-primary"] {
  background: var(--text) !important; color:#fff !important;
  border:none !important; border-radius:var(--r-md) !important;
  font-family:'DM Sans',sans-serif !important;
  font-size:15px !important; font-weight:500 !important;
  width:100% !important; padding:14px !important;
  transition: background var(--tr), transform var(--tr) !important;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover,
button[data-testid="baseButton-primary"]:hover {
  background: var(--amber) !important; transform:translateY(-1px) !important;
}
button[data-testid="baseButton-secondary"] {
  background:transparent !important; color:var(--muted) !important;
  border:1.5px solid var(--border) !important;
  border-radius:var(--r-md) !important;
  font-family:'DM Sans',sans-serif !important;
  font-size:14px !important; width:100% !important; padding:13px !important;
  transition: all var(--tr) !important;
}
button[data-testid="baseButton-secondary"]:hover {
  border-color:var(--amber) !important; color:var(--amber) !important;
}

/* ── Divider ── */
.vg-divider { display:flex; align-items:center; gap:12px; margin:20px 0; }
.vg-divider::before,.vg-divider::after { content:'';flex:1;height:1px;background:var(--border); }
.vg-divider span { font-size:12px; color:var(--muted); }

/* ── HERO ── */
.vg-hero {
  position:relative; text-align:center;
  padding:72px 24px 56px; overflow:hidden;
  animation: fadeUp .5s ease both;
}
.vg-hero-bg {
  position:absolute; inset:0;
  background:radial-gradient(ellipse at 50% 100%,rgba(201,133,58,.18) 0%,transparent 70%);
  pointer-events:none;
}
.vg-hero-tag {
  display:inline-block; background:var(--amber-p);
  border:1px solid rgba(201,133,58,.3); color:var(--amber);
  font-size:11px; font-weight:500; letter-spacing:.1em; text-transform:uppercase;
  padding:6px 16px; border-radius:20px; margin-bottom:20px;
}
.vg-hero-title {
  font-family:'Playfair Display',serif;
  font-size:clamp(40px,6vw,68px); font-weight:700;
  color:var(--text); line-height:1.1; margin-bottom:16px;
}
.vg-hero-title em { color:var(--amber); font-style:italic; }
.vg-hero-sub { font-size:16px; color:var(--muted); max-width:480px; margin:0 auto; line-height:1.7; }

/* ── PLANNER CARD ── */
.vg-planner-wrap { max-width:700px; margin:0 auto; padding:0 24px 60px; }
.vg-planner-card {
  background:#fff; border:1px solid var(--border);
  border-radius:var(--r-xl); padding:36px 40px;
  box-shadow:var(--sh-lg); animation:fadeUp .6s .1s ease both;
}
@media(max-width:768px){ .vg-planner-card{padding:24px 20px;} }
.vg-planner-title { font-family:'Playfair Display',serif; font-size:22px; font-weight:700; color:var(--text); margin-bottom:24px; }

/* Trip type pills */
.trip-pills { display:flex; flex-wrap:wrap; gap:10px; margin-bottom:8px; }
.trip-pill {
  padding:10px 18px; border:1.5px solid var(--border);
  border-radius:var(--r-md); cursor:pointer;
  font-family:'DM Sans',sans-serif; font-size:13px; font-weight:500;
  color:var(--muted); background:var(--sand2);
  transition:all var(--tr); display:flex; align-items:center; gap:8px;
}
.trip-pill:hover,.trip-pill.active { border-color:var(--amber); color:var(--amber); background:var(--amber-p); }

/* ── QUICK PICKS ── */
.vg-quick { margin-top:24px; text-align:center; }
.vg-quick-lbl { font-size:11px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); margin-bottom:12px; }
.vg-quick-tags { display:flex; gap:8px; justify-content:center; flex-wrap:wrap; }
.vg-quick-tag {
  background:#fff; border:1px solid var(--border); border-radius:20px;
  padding:7px 14px; font-size:13px; color:var(--muted);
  cursor:pointer; font-family:'DM Sans',sans-serif; transition:all var(--tr);
}
.vg-quick-tag:hover { border-color:var(--amber); color:var(--amber); background:var(--amber-p); }

/* ── OUTPUT ── */
.vg-output-hdr {
  position:sticky; top:58px; z-index:50;
  background:var(--sand); border-bottom:1px solid var(--border);
  padding:12px 32px; display:flex; align-items:center; gap:14px; flex-wrap:wrap;
}
.vg-back-btn {
  background:var(--sand2); border:1px solid var(--border);
  border-radius:var(--r-sm); padding:8px 16px;
  font-family:'DM Sans',sans-serif; font-size:14px; color:var(--text);
  cursor:pointer; transition:all var(--tr); white-space:nowrap;
}
.vg-back-btn:hover { border-color:var(--amber); color:var(--amber); }
.vg-output-dest { font-family:'Playfair Display',serif; font-size:20px; font-weight:700; color:var(--text); flex:1; }
.vg-output-meta { font-size:13px; color:var(--muted); }
.vg-action-btn {
  padding:8px 14px; background:var(--amber-p);
  border:1px solid rgba(201,133,58,.35); border-radius:var(--r-sm);
  font-family:'DM Sans',sans-serif; font-size:13px; font-weight:500;
  color:var(--amber); cursor:pointer; transition:background var(--tr);
}
.vg-action-btn:hover { background:rgba(201,133,58,.22); }

/* ── RESULTS ── */
.vg-results { max-width:1100px; margin:0 auto; padding:24px 32px 80px; }
.vg-stats-row { display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; margin-bottom:28px; }
.vg-stat-card {
  background:#fff; border:1px solid var(--border);
  border-radius:var(--r-md); padding:16px 18px; text-align:center;
  animation:fadeUp .4s ease both;
}
.vg-stat-val { font-family:'Playfair Display',serif; font-size:20px; font-weight:700; color:var(--amber); margin-bottom:4px; }
.vg-stat-lbl { font-size:11px; text-transform:uppercase; letter-spacing:.07em; color:var(--muted); }

/* Results grid */
.vg-grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; }
.vg-grid .full { grid-column:1/-1; }
@media(max-width:768px){ .vg-grid{grid-template-columns:1fr;} .vg-grid .full{grid-column:1;} }

/* Card */
.vg-card {
  background:#fff; border:1px solid var(--border);
  border-radius:var(--r-lg); padding:24px 28px;
  box-shadow:var(--sh-sm); animation:fadeUp .5s ease both;
}
.vg-card-hdr {
  display:flex; align-items:center; gap:10px;
  margin-bottom:18px; padding-bottom:14px; border-bottom:1px solid var(--border);
}
.vg-card-icon {
  width:36px; height:36px; border-radius:var(--r-sm);
  background:var(--amber-p); display:flex;
  align-items:center; justify-content:center; font-size:18px; flex-shrink:0;
}
.vg-card-title { font-family:'Playfair Display',serif; font-size:17px; font-weight:700; color:var(--text); }

/* Day block */
.vg-day {
  display:flex; align-items:flex-start; gap:12px;
  padding:12px 14px; background:var(--sand2); border-radius:var(--r-sm);
  margin-bottom:8px; font-size:14px; line-height:1.5;
}
.vg-day-num {
  font-size:10px; font-weight:500; letter-spacing:.06em;
  text-transform:uppercase; color:var(--amber); background:var(--amber-p);
  padding:3px 8px; border-radius:10px; white-space:nowrap; margin-top:2px; flex-shrink:0;
}

/* List item */
.vg-li {
  display:flex; align-items:center; justify-content:space-between;
  padding:11px 0; border-bottom:1px solid var(--border); gap:10px;
}
.vg-li:last-child { border-bottom:none; }
.vg-li-name { font-size:14px; font-weight:500; color:var(--text); }
.vg-li-sub  { font-size:12px; color:var(--muted); margin-top:2px; }

/* Mini buttons */
.vg-btn {
  padding:7px 14px; border:none; border-radius:var(--r-sm);
  font-family:'DM Sans',sans-serif; font-size:12px; font-weight:500;
  cursor:pointer; text-decoration:none; display:inline-block;
  transition:opacity var(--tr), transform var(--tr); white-space:nowrap;
}
.vg-btn:hover { opacity:.85; transform:translateY(-1px); }
.btn-map     { background:#E8F5E9; color:#1B5E20; }
.btn-book    { background:#E3F2FD; color:#0D47A1; }
.btn-reserve { background:#FFEBEE; color:#B71C1C; }
.btn-cab     { background:var(--text); color:#fff; }

/* Food tags */
.vg-food-tags { display:flex; flex-wrap:wrap; gap:8px; }
.vg-food-tag {
  background:var(--amber-p); border:1px solid rgba(201,133,58,.25);
  color:var(--amber); border-radius:20px; padding:5px 12px; font-size:12px;
}

/* Tips */
.vg-tips { display:flex; flex-direction:column; gap:10px; }
.vg-tip  { display:flex; align-items:flex-start; gap:10px; font-size:13px; color:var(--text); line-height:1.5; }
.vg-tip-icon { font-size:16px; flex-shrink:0; margin-top:1px; }

/* Similar */
.vg-similars { display:flex; flex-wrap:wrap; gap:10px; }
.vg-sim-btn {
  background:var(--sand2); border:1px solid var(--border);
  border-radius:var(--r-md); padding:10px 16px;
  font-family:'DM Sans',sans-serif; font-size:13px; color:var(--text);
  cursor:pointer; transition:all var(--tr); display:flex; align-items:center; gap:6px;
}
.vg-sim-btn:hover { border-color:var(--amber); color:var(--amber); background:var(--amber-p); }

/* ── DASHBOARD ── */
.vg-dash-stats {
  display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  gap:16px; margin-bottom:32px;
}
.vg-dash-stat {
  background:#fff; border:1px solid var(--border);
  border-radius:var(--r-lg); padding:20px 24px;
  box-shadow:var(--sh-sm); animation:fadeUp .4s ease both;
}
.vg-dash-stat-val { font-family:'Playfair Display',serif; font-size:28px; color:var(--amber); font-weight:700; }
.vg-dash-stat-lbl { font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; margin-top:4px; }

.vg-trip-card {
  background:#fff; border:1px solid var(--border); border-radius:var(--r-lg);
  padding:20px 24px; margin-bottom:14px; box-shadow:var(--sh-sm);
  display:flex; align-items:center; gap:16px; animation:fadeUp .4s ease both;
}
.vg-trip-icon { font-size:28px; }
.vg-trip-info { flex:1; }
.vg-trip-dest { font-family:'Playfair Display',serif; font-size:17px; font-weight:700; color:var(--text); }
.vg-trip-meta { font-size:12px; color:var(--muted); margin-top:4px; }
.vg-trip-badge {
  background:var(--amber-p); border:1px solid rgba(201,133,58,.3);
  color:var(--amber); font-size:11px; font-weight:500;
  padding:4px 10px; border-radius:12px;
}

/* Streamlit expander override */
details[data-testid="stExpander"] {
  border: 1px solid var(--border) !important;
  border-radius: var(--r-lg) !important;
  background: #fff !important;
  box-shadow: var(--sh-sm) !important;
  margin-bottom: 12px !important;
}
details[data-testid="stExpander"] summary {
  font-family: 'Playfair Display', serif !important;
  font-size: 16px !important;
  font-weight: 700 !important;
  padding: 16px 20px !important;
}

/* Streamlit spinner */
div[data-testid="stSpinner"] > div {
  border-color: var(--border) !important;
  border-top-color: var(--amber) !important;
}

/* Streamlit alert/info/success overrides */
div[data-testid="stAlert"] {
  border-radius: var(--r-md) !important;
}

/* Streamlit tabs */
button[data-baseweb="tab"] {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
  color: var(--amber) !important;
}
div[data-baseweb="tab-highlight"] {
  background: var(--amber) !important;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  NAVBAR
# ═══════════════════════════════════════════════════════════════
def render_nav():
    user_name = st.session_state.get("name", "")
    logged_in = bool(st.session_state.user_id)

    col_logo, col_links = st.columns([3, 2])
    with col_logo:
        st.markdown("""
        <div class="vg-nav">
          <div class="vg-nav-inner">
            <div class="vg-logo">Voyager <span class="vg-dot"></span></div>
          </div>
        </div>""", unsafe_allow_html=True)

    # Nav buttons in a row
    nav_cols = st.columns([5, 1, 1, 1])
    with nav_cols[0]:
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
    with nav_cols[1]:
        if st.button("🏠 Home", key="nav_home", use_container_width=True):
            go_to("home")
    with nav_cols[2]:
        if logged_in:
            if st.button("📊 Dashboard", key="nav_dash", use_container_width=True):
                go_to("dashboard")
        else:
            if st.button("🔑 Login", key="nav_login", use_container_width=True):
                go_to("login")
    with nav_cols[3]:
        if logged_in:
            if st.button("👋 Logout", key="nav_logout", use_container_width=True):
                st.session_state.user_id = None
                st.session_state.name = ""
                go_to("login")

# ═══════════════════════════════════════════════════════════════
#  LOGIN / REGISTER VIEW
# ═══════════════════════════════════════════════════════════════
def login_view():
    st.markdown("""
    <div class="login-grid">
      <!-- Visual panel -->
      <div class="vp">
        <div class="vp-bg"></div>
        <div class="dest-grid">
          <div class="dest-tile">Santorini</div>
          <div class="dest-tile">Kyoto</div>
          <div class="dest-tile">Marrakech</div>
          <div class="dest-tile">Patagonia</div>
          <div class="dest-tile">Maldives</div>
          <div class="dest-tile">Rajasthan</div>
        </div>
        <div class="vp-content">
          <div class="vp-tag">✦ AI-Powered Travel</div>
          <h1 class="vp-headline">Plan your next<br><em>great escape</em><br>in seconds.</h1>
          <p class="vp-sub">Tell us where you want to go, and our AI crafts a perfect itinerary with hotels, food, and transport — tailored just for you.</p>
          <div class="vp-stats">
            <div><div class="vp-stat-num">500+</div><div class="vp-stat-lbl">Destinations</div></div>
            <div><div class="vp-stat-num">AI</div><div class="vp-stat-lbl">Itineraries</div></div>
            <div><div class="vp-stat-num">Free</div><div class="vp-stat-lbl">To use</div></div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Fake right panel — Streamlit forms go here but we style them
    st.markdown('<div class="fp"><div class="fp-inner">', unsafe_allow_html=True)
    st.markdown('<div class="fp-logo">Voyager <span class="vg-dot"></span></div>', unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Sign In", "Create Account"])

    with tab_login:
        st.markdown('<p class="fp-sub">Welcome back — sign in to continue</p>', unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In →", type="primary", use_container_width=True)
            if submitted:
                if not username or not password:
                    st.error("Please fill in all fields.")
                else:
                    with get_db() as db:
                        user = db.query(User).filter_by(username=username).first()
                        if user and check_password(password, user.password):
                            st.session_state.user_id = user.id
                            st.session_state.name = user.name
                            go_to("home")
                        else:
                            st.error("❌ Invalid username or password.")

    with tab_register:
        st.markdown('<p class="fp-sub">Create your free account</p>', unsafe_allow_html=True)
        with st.form("register_form"):
            new_name     = st.text_input("Full Name", placeholder="Your full name")
            new_email    = st.text_input("Email", placeholder="you@email.com")
            new_username = st.text_input("Username", placeholder="Choose a username")
            new_password = st.text_input("Password", type="password", placeholder="Create a password")
            reg_submit   = st.form_submit_button("Create Account →", type="primary", use_container_width=True)
            if reg_submit:
                if not all([new_name, new_email, new_username, new_password]):
                    st.error("All fields are required.")
                else:
                    with get_db() as db:
                        if db.query(User).filter_by(username=new_username).first():
                            st.error("Username already taken.")
                        elif db.query(User).filter_by(email=new_email).first():
                            st.error("Email already registered.")
                        else:
                            user = User(username=new_username, email=new_email,
                                        name=new_name, password=hash_password(new_password))
                            db.add(user); db.commit()
                            st.session_state.user_id = user.id
                            st.session_state.name = new_name
                            go_to("home")

    st.markdown('<div class="vg-divider"><span>or</span></div>', unsafe_allow_html=True)
    if st.button("Continue as Guest →", use_container_width=True):
        st.session_state.user_id = None
        go_to("home")

    st.markdown('</div></div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  RENDER ITINERARY
# ═══════════════════════════════════════════════════════════════
def render_itinerary(plan_data, meta):
    dest  = meta.get("destination", "Destination")
    days  = meta.get("days", "?")
    bgt   = meta.get("budget", 0)
    ttype = meta.get("trip_type", "")

    # Output header bar
    st.markdown(f"""
    <div class="vg-output-hdr">
      <div class="vg-output-dest">✈️ {dest}</div>
      <div class="vg-output-meta">{days} Days · ₹{bgt:,} · {ttype}</div>
    </div>""", unsafe_allow_html=True)

    # City tabs
    city_names = [p.get("city", f"City {i+1}") for i, p in enumerate(plan_data)]
    tabs = st.tabs(city_names)

    for tab, city_plan in zip(tabs, plan_data):
        with tab:
            city     = city_plan.get("city", "Destination")
            plan_txt = city_plan.get("plan", "")
            places   = city_plan.get("places", [])
            hotels   = city_plan.get("hotels", [])
            food     = city_plan.get("food", {})
            transport= city_plan.get("transport", {})
            tips     = city_plan.get("tips", [])
            similar  = city_plan.get("similar", [])

            # Stats row
            street_food_count = len(food.get("street_food", []))
            hotel_count       = len(hotels)
            place_count       = len(places)
            st.markdown(f"""
            <div class="vg-results">
            <div class="vg-stats-row">
              <div class="vg-stat-card"><div class="vg-stat-val">{place_count}</div><div class="vg-stat-lbl">Places</div></div>
              <div class="vg-stat-card"><div class="vg-stat-val">{hotel_count}</div><div class="vg-stat-lbl">Hotels</div></div>
              <div class="vg-stat-card"><div class="vg-stat-val">{street_food_count}</div><div class="vg-stat-lbl">Dishes</div></div>
              <div class="vg-stat-card"><div class="vg-stat-val">₹{bgt:,}</div><div class="vg-stat-lbl">Budget</div></div>
            </div>""", unsafe_allow_html=True)

            # Results grid
            st.markdown('<div class="vg-grid">', unsafe_allow_html=True)

            # ── Day-by-day Plan (full width) ──
            days_html = ""
            for line in plan_txt.strip().split("\n"):
                if not line.strip(): continue
                if line.startswith("Day"):
                    colon = line.find(":")
                    day_label = line[:colon] if colon > -1 else "Day"
                    content   = line[colon+1:].strip() if colon > -1 else line
                    days_html += f'<div class="vg-day"><span class="vg-day-num">{day_label}</span><span>{content}</span></div>'
                else:
                    days_html += f'<div style="font-size:14px;color:var(--muted);padding:6px 0">{line}</div>'

            st.markdown(f"""
            <div class="vg-card full">
              <div class="vg-card-hdr">
                <div class="vg-card-icon">🗓️</div>
                <div class="vg-card-title">Day-by-Day Itinerary</div>
              </div>
              {days_html}
            </div>""", unsafe_allow_html=True)

            # ── Places to Visit ──
            places_html = ""
            for place in places:
                n = place.get("name", "")
                query = n.replace(" ", "+")
                places_html += f"""
                <div class="vg-li">
                  <div><div class="vg-li-name">📍 {n}</div></div>
                  <a href="https://www.google.com/maps/search/{query}" target="_blank" class="vg-btn btn-map">Map</a>
                </div>"""

            st.markdown(f"""
            <div class="vg-card">
              <div class="vg-card-hdr">
                <div class="vg-card-icon">📍</div>
                <div class="vg-card-title">Places to Visit</div>
              </div>
              {"".join([f'<div class="vg-li"><div class="vg-li-name">📍 {p.get("name","")}</div><a href="https://www.google.com/maps/search/{p.get("name","").replace(" ","+")}+{city}" target="_blank" class="vg-btn btn-map">Map</a></div>' for p in places]) or '<p style="color:var(--muted);font-size:14px">No specific places listed.</p>'}
            </div>""", unsafe_allow_html=True)

            # ── Hotels ──
            type_icons = {"budget": "🏨", "mid": "🏩", "luxury": "🌟"}
            hotels_html = "".join([
                f'<div class="vg-li"><div><div class="vg-li-name">{type_icons.get(h.get("type",""),"🏨")} {h.get("name","")}</div><div class="vg-li-sub">{h.get("type","").title()}</div></div><a href="{h.get("link","#")}" target="_blank" class="vg-btn btn-book">Book</a></div>'
                for h in hotels
            ]) or '<p style="color:var(--muted);font-size:14px">No hotels listed.</p>'

            st.markdown(f"""
            <div class="vg-card">
              <div class="vg-card-hdr">
                <div class="vg-card-icon">🏨</div>
                <div class="vg-card-title">Where to Stay</div>
              </div>
              {hotels_html}
            </div>""", unsafe_allow_html=True)

            # ── Food ──
            sf_tags = "".join([f'<span class="vg-food-tag">{d}</span>' for d in food.get("street_food", [])])
            rest_html = "".join([
                f'<div class="vg-li"><div class="vg-li-name">🍽️ {r.get("name","")}</div><a href="{r.get("link","#")}" target="_blank" class="vg-btn btn-reserve">Reserve</a></div>'
                for r in food.get("restaurants", [])
            ])

            st.markdown(f"""
            <div class="vg-card">
              <div class="vg-card-hdr">
                <div class="vg-card-icon">🍜</div>
                <div class="vg-card-title">Food & Dining</div>
              </div>
              <div style="margin-bottom:16px">
                <div class="vg-label" style="margin-bottom:10px">Must-Try Street Food</div>
                <div class="vg-food-tags">{sf_tags or "–"}</div>
              </div>
              <div>
                <div class="vg-label" style="margin-bottom:10px">Restaurants</div>
                {rest_html or '<p style="color:var(--muted);font-size:14px">No restaurants listed.</p>'}
              </div>
            </div>""", unsafe_allow_html=True)

            # ── Transport ──
            cabs = transport.get("cabs", [])
            cabs_html = "".join([
                f'<a href="{c.get("link","#")}" target="_blank" class="vg-btn btn-cab">{c.get("name","")}</a>'
                for c in cabs
            ])

            st.markdown(f"""
            <div class="vg-card">
              <div class="vg-card-hdr">
                <div class="vg-card-icon">🚕</div>
                <div class="vg-card-title">Getting Around</div>
              </div>
              <div style="display:flex;flex-wrap:wrap;gap:8px">{cabs_html or "–"}</div>
            </div>""", unsafe_allow_html=True)

            # ── Tips ──
            if tips:
                tips_html = "".join([f'<div class="vg-tip"><span class="vg-tip-icon">💡</span><span>{t}</span></div>' for t in tips])
                st.markdown(f"""
                <div class="vg-card full">
                  <div class="vg-card-hdr">
                    <div class="vg-card-icon">💡</div>
                    <div class="vg-card-title">Travel Tips</div>
                  </div>
                  <div class="vg-tips">{tips_html}</div>
                </div>""", unsafe_allow_html=True)

            # ── Similar Destinations ──
            if similar:
                sim_html = "".join([f'<span class="vg-sim-btn">🗺️ {s}</span>' for s in similar])
                st.markdown(f"""
                <div class="vg-card full">
                  <div class="vg-card-hdr">
                    <div class="vg-card-icon">🗺️</div>
                    <div class="vg-card-title">You Might Also Like</div>
                  </div>
                  <div class="vg-similars">{sim_html}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown('</div></div>', unsafe_allow_html=True)  # close vg-grid + vg-results

# ═══════════════════════════════════════════════════════════════
#  HOME VIEW
# ═══════════════════════════════════════════════════════════════
def home_view():
    render_nav()

    # If itinerary already generated, show it
    if st.session_state.current_plan:
        meta = st.session_state.current_plan_meta or {}

        # Action bar below nav
        action_col1, action_col2, action_col3 = st.columns([1, 1, 4])
        with action_col1:
            if st.button("← New Plan", key="back_btn", use_container_width=True):
                st.session_state.current_plan = None
                st.session_state.current_plan_meta = None
                st.rerun()
        with action_col2:
            if st.session_state.user_id:
                if st.button("💾 Save Trip", key="save_btn", use_container_width=True):
                    share_id = str(uuid.uuid4())[:10]
                    with get_db() as db:
                        trip = SavedTrip(
                            user_id=st.session_state.user_id,
                            share_id=share_id,
                            destination=meta.get("destination",""),
                            days=meta.get("days"),
                            budget=meta.get("budget"),
                            trip_type=meta.get("trip_type",""),
                            plan_json=json.dumps(st.session_state.current_plan)
                        )
                        db.add(trip); db.commit()
                    st.success(f"✅ Trip saved! Share code: `{share_id}`")

        render_itinerary(st.session_state.current_plan, meta)

        # Email form at the bottom
        st.markdown("---")
        with st.expander("📧 Email this itinerary"):
            with st.form("email_form"):
                email_addr = st.text_input("Your email address")
                if st.form_submit_button("Send →", type="primary"):
                    if email_addr:
                        try:
                            send_itinerary_email(email_addr, meta.get("destination",""), st.session_state.current_plan)
                            st.success("✅ Email sent!")
                        except Exception as e:
                            st.error(f"Failed: {e}")
        return

    # ── Hero ──
    st.markdown("""
    <div class="vg-hero">
      <div class="vg-hero-bg"></div>
      <div class="vg-hero-tag">✦ AI-Powered Travel Planning</div>
      <h1 class="vg-hero-title">Where do you want<br>to go <em>next?</em></h1>
      <p class="vg-hero-sub">Tell us your destination and we'll craft a personalised itinerary with hotels, food, and transport — powered by AI.</p>
    </div>""", unsafe_allow_html=True)

    # ── Planner Card ──
    st.markdown('<div class="vg-planner-wrap"><div class="vg-planner-card">', unsafe_allow_html=True)
    st.markdown('<div class="vg-planner-title">Plan Your Trip</div>', unsafe_allow_html=True)

    with st.form("planner_form"):
        destination = st.text_input("🌍 Destination", placeholder="e.g. Goa, Mumbai, Jaipur (comma separated)")
        c1, c2 = st.columns(2)
        with c1:
            days   = st.number_input("📅 Number of Days", min_value=1, max_value=30, value=3)
        with c2:
            budget = st.number_input("💰 Budget (₹)", min_value=500, max_value=1000000, value=15000, step=1000)

        st.markdown('<div class="vg-label" style="margin-top:8px">Trip Type</div>', unsafe_allow_html=True)
        trip_type = st.selectbox("", ["Solo 🎒", "Family 👨‍👩‍👧", "Friends 🎉", "Honeymoon 💑"],
                                 label_visibility="collapsed")
        trip_type_clean = trip_type.split(" ")[0]  # strip emoji

        submit = st.form_submit_button("Generate Itinerary →", type="primary", use_container_width=True)

    st.markdown('</div></div>', unsafe_allow_html=True)

    # Quick picks
    st.markdown("""
    <div class="vg-quick">
      <div class="vg-quick-lbl">Popular Destinations</div>
      <div class="vg-quick-tags">
        <span class="vg-quick-tag">🏖️ Goa</span>
        <span class="vg-quick-tag">🕌 Jaipur</span>
        <span class="vg-quick-tag">🏔️ Manali</span>
        <span class="vg-quick-tag">🌊 Andaman</span>
        <span class="vg-quick-tag">🏯 Agra</span>
        <span class="vg-quick-tag">🌴 Kerala</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if submit and destination:
        with st.spinner("✨ Generating your personalised itinerary…"):
            city_list = [c.strip() for c in destination.split(",")]
            result = []
            if len(city_list) == 1:
                city = city_list[0]
                ai = generate_with_ai(city, days, budget, trip_type_clean)
                result.append(ai if ai else generate_static_fallback(city, days, budget, trip_type_clean))
            else:
                num_cities    = len(city_list)
                days_per_city = int(days) // num_cities
                extra_days    = int(days) % num_cities
                for i, city in enumerate(city_list):
                    city_days = days_per_city + (1 if i < extra_days else 0)
                    ai = generate_with_ai(city, city_days, budget, trip_type_clean)
                    result.append(ai if ai else generate_static_fallback(city, city_days, budget, trip_type_clean))

            st.session_state.current_plan = result
            st.session_state.current_plan_meta = {
                "destination": destination, "days": days,
                "budget": budget, "trip_type": trip_type_clean
            }
            st.rerun()

# ═══════════════════════════════════════════════════════════════
#  DASHBOARD VIEW
# ═══════════════════════════════════════════════════════════════
def dashboard_view():
    render_nav()

    if not st.session_state.user_id:
        st.warning("Please sign in to view your dashboard.")
        if st.button("Go to Login"):
            go_to("login")
        return

    with get_db() as db:
        user  = db.query(User).get(st.session_state.user_id)
        trips = db.query(SavedTrip).filter_by(user_id=user.id).order_by(SavedTrip.created_at.desc()).all()

        total_budget = sum(t.budget or 0 for t in trips)
        fav_type     = max(set(t.trip_type for t in trips),
                           key=lambda x: [t.trip_type for t in trips].count(x)) if trips else "—"

        # Header
        st.markdown(f"""
        <div style="padding:32px 32px 8px;max-width:1100px;margin:0 auto;animation:fadeUp .4s ease both">
          <div class="vg-hero-tag">Your Journey History</div>
          <h1 style="font-family:'Playfair Display',serif;font-size:36px;color:var(--text);margin:8px 0 4px">
            Welcome back, {user.name} ✈️
          </h1>
          <p style="color:var(--muted);font-size:15px">Here are all the adventures you've planned.</p>
        </div>""", unsafe_allow_html=True)

        # Stats
        st.markdown(f"""
        <div style="max-width:1100px;margin:0 auto;padding:0 32px">
        <div class="vg-dash-stats">
          <div class="vg-dash-stat"><div class="vg-dash-stat-val">{len(trips)}</div><div class="vg-dash-stat-lbl">Trips Planned</div></div>
          <div class="vg-dash-stat"><div class="vg-dash-stat-val">₹{total_budget:,}</div><div class="vg-dash-stat-lbl">Total Budget</div></div>
          <div class="vg-dash-stat"><div class="vg-dash-stat-val">{fav_type}</div><div class="vg-dash-stat-lbl">Favourite Style</div></div>
        </div>""", unsafe_allow_html=True)

        if not trips:
            st.info("You haven't saved any trips yet. Generate one and hit 'Save Trip'!")
        else:
            st.markdown('<div style="margin-top:8px">', unsafe_allow_html=True)
            for trip in trips:
                type_icons = {"Solo": "🎒", "Family": "👨‍👩‍👧", "Friends": "🎉", "Honeymoon": "💑"}
                icon = type_icons.get(trip.trip_type, "✈️")

                with st.expander(f"{icon}  {trip.destination}  —  {trip.days} Days · ₹{trip.budget:,}", expanded=False):
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Trip Type:** {trip.trip_type}")
                    c2.markdown(f"**Saved on:** {trip.created_at.strftime('%d %b %Y')}")
                    c3.markdown(f"**Share Code:** `{trip.share_id}`")
                    bt1, bt2 = st.columns(2)
                    with bt1:
                        if st.button("📄 View Details", key=f"view_{trip.id}", use_container_width=True):
                            st.session_state.current_plan = json.loads(trip.plan_json)
                            st.session_state.current_plan_meta = {
                                "destination": trip.destination, "days": trip.days,
                                "budget": trip.budget, "trip_type": trip.trip_type
                            }
                            go_to("home")
                    with bt2:
                        if st.button("🗑️ Delete", key=f"del_{trip.id}", use_container_width=True):
                            db.delete(trip); db.commit()
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════════
inject_css()

if st.session_state.view == "login":
    login_view()
elif st.session_state.view == "home":
    home_view()
elif st.session_state.view == "dashboard":
    dashboard_view()