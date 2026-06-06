"""
╔══════════════════════════════════════════════════════════════╗
║  VOYAGER AI — app.py  (v4 — FIXED & COMPLETE)               ║
║  Fixes:                                                      ║
║  • All missing templates added (dashboard, shared, email,    ║
║    404, cities)                                              ║
║  • Auth (register/login/logout) fully working               ║
║  • Multi-city AI prompt returns correct array format        ║
║  • Weather proxied server-side to avoid CORS                ║
║  • /api/cities endpoint for autocomplete                    ║
║  • Proper error handling throughout                         ║
║  • Guest session handled correctly                          ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, json, uuid, re
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
load_dotenv()

from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, abort)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic
import urllib.request

# ── App setup ──────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "voyager-dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///voyager.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["MAIL_SERVER"]         = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"]           = int(os.getenv("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"]        = os.getenv("MAIL_USE_TLS", "True") == "True"
app.config["MAIL_USERNAME"]       = os.getenv("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"]       = os.getenv("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "noreply@voyager.ai")

db      = SQLAlchemy(app)
bcrypt  = Bcrypt(app)
mail    = Mail(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day"])

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# ── Static data loaders ───────────────────────────────────────
def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}

static_places      = _load_json("data/places.json")
static_hotels      = _load_json("data/hotels.json")
static_restaurants = _load_json("data/restaurants.json")
static_transport   = _load_json("data/transport.json")
static_cities      = _load_json("data/cities.json")


# ══════════════════════════════════════════════════════════════
#  DATABASE MODELS
# ══════════════════════════════════════════════════════════════
class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    name       = db.Column(db.String(100), nullable=False)
    password   = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trips      = db.relationship("SavedTrip", backref="user", lazy=True)


class SavedTrip(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    share_id    = db.Column(db.String(12), unique=True, nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    days        = db.Column(db.Integer)
    budget      = db.Column(db.Integer)
    trip_type   = db.Column(db.String(50))
    plan_json   = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        hashed = bcrypt.generate_password_hash("admin123").decode("utf-8")
        db.session.add(User(username="admin", email="admin@voyager.ai",
                            name="Admin User", password=hashed))
        db.session.commit()


# ══════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id") and not session.get("guest"):
            return redirect(url_for("login_page") + "?error=Please+sign+in+first")
        return f(*args, **kwargs)
    return decorated


def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None


# ══════════════════════════════════════════════════════════════
#  AI ITINERARY GENERATION  (FIXED — returns list always)
# ══════════════════════════════════════════════════════════════
def generate_with_ai(destination, days, budget, trip_type):
    """Call Claude to generate itinerary. Always returns a dict or None."""
    budget_tier = (
        "budget hostels and street food stalls"
        if int(budget) < 10000 else
        "mid-range hotels and local restaurants"
        if int(budget) < 50000 else
        "luxury resorts and fine dining"
    )
    prompt = f"""You are an expert Indian travel planner. Create a detailed {days}-day itinerary for {destination}.
Trip type: {trip_type} | Total budget: ₹{budget:,} | Accommodation level: {budget_tier}

Return ONLY valid JSON — no markdown fences, no explanation:
{{
  "city": "{destination}",
  "plan": "Day 1: Morning at ..., afternoon ..., evening ...\\nDay 2: ...",
  "places": [
    {{"name": "Place Name"}}
  ],
  "hotels": [
    {{"name": "Hotel Name", "type": "budget", "link": "https://www.booking.com/search.html?ss={destination}"}},
    {{"name": "Hotel Name", "type": "mid",    "link": "https://www.booking.com/search.html?ss={destination}"}},
    {{"name": "Hotel Name", "type": "luxury", "link": "https://www.booking.com/search.html?ss={destination}"}}
  ],
  "food": {{
    "street_food": ["Dish 1", "Dish 2", "Dish 3", "Dish 4"],
    "restaurants": [
      {{"name": "Restaurant Name", "link": "https://www.zomato.com/search?q={destination}"}}
    ]
  }},
  "transport": {{
    "cabs": [
      {{"name": "Ola",   "link": "https://www.olacabs.com"}},
      {{"name": "Uber",  "link": "https://www.uber.com/in/en/"}},
      {{"name": "Rapido","link": "https://rapido.bike"}}
    ]
  }},
  "tips": ["Tip 1", "Tip 2", "Tip 3"],
  "similar": ["City1", "City2", "City3"]
}}

Be specific to {destination}. Tailor for {trip_type}. Use realistic local hotel/restaurant names."""

    try:
        response = anthropic_client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
        text = text.strip()
        return json.loads(text)
    except Exception as e:
        print(f"[AI ERROR] {e}")
        return None


def generate_static_fallback(city, days, budget, trip_type):
    city_places = static_places.get(city, [])
    fallback = ["Shopping", "Leisure", "Local exploration", "Café hopping", "Street food tour"]
    prefix   = {"Solo": "Explore", "Family": "Visit family-friendly spots at",
                 "Friends": "Enjoy with friends at", "Honeymoon": "Romantic visit to"}.get(trip_type, "Visit")
    per_day  = max(1, len(city_places) // days) if city_places else 1
    lines, idx = [], 0

    for d in range(days):
        chunk = city_places[idx:idx + per_day]; idx += per_day
        if chunk:
            text = f"{prefix} {', '.join(p['name'] for p in chunk)}"
        else:
            act = fallback[d % len(fallback)]
            text = f"{act} and relaxation"
        lines.append(f"Day {d+1}: {text}")

    city_hotels = [h for h in static_hotels.get(city, [])
                   if int(budget) >= 10000 or h.get("type") == "budget"]
    return {
        "city":      city,
        "plan":      "\n".join(lines),
        "places":    city_places,
        "hotels":    city_hotels,
        "food":      static_restaurants.get(city, {"street_food": [], "restaurants": []}),
        "transport": static_transport.get(city, {"cabs": []}),
        "tips":      ["Download offline maps before you travel.",
                      "Carry cash for smaller towns.",
                      "Keep digital copies of all documents."],
        "similar":   []
    }


# ══════════════════════════════════════════════════════════════
#  AUTH ROUTES  (FIXED)
# ══════════════════════════════════════════════════════════════
@app.route("/")
def login_page():
    if session.get("user_id"):
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def handle_login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return redirect(url_for("login_page") + "?error=Please+fill+all+fields")

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        session.clear()
        session["user_id"] = user.id
        session["name"]    = user.name
        session.permanent  = True
        return redirect(url_for("home"))
    return redirect(url_for("login_page") + "?error=Invalid+username+or+password")


@app.route("/register", methods=["POST"])
def handle_register():
    fullname = request.form.get("fullname", "").strip()
    email    = request.form.get("email",    "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not all([fullname, email, username, password]):
        return redirect(url_for("login_page") + "?tab=register&error=All+fields+are+required")
    if len(password) < 6:
        return redirect(url_for("login_page") + "?tab=register&error=Password+must+be+at+least+6+characters")
    if User.query.filter_by(username=username).first():
        return redirect(url_for("login_page") + "?tab=register&error=Username+already+taken")
    if User.query.filter_by(email=email).first():
        return redirect(url_for("login_page") + "?tab=register&error=Email+already+registered")

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user   = User(username=username, email=email, name=fullname, password=hashed)
    db.session.add(user)
    db.session.commit()

    session.clear()
    session["user_id"] = user.id
    session["name"]    = fullname
    session.permanent  = True
    return redirect(url_for("home") + "?success=Welcome+to+Voyager,+" + fullname.split()[0] + "!")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page") + "?success=Signed+out+successfully")


# ══════════════════════════════════════════════════════════════
#  MAIN APP ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/home")
def home():
    if not session.get("user_id"):
        session["guest"] = True
    user = current_user()
    return render_template("index.html", user=user)


@app.route("/dashboard")
@login_required
def dashboard():
    user  = current_user()
    if not user:
        return redirect(url_for("login_page"))
    trips = SavedTrip.query.filter_by(user_id=user.id).order_by(SavedTrip.created_at.desc()).all()
    total_budget  = sum(t.budget or 0 for t in trips)
    destinations  = list({t.destination for t in trips})
    fav_type      = (max(set(t.trip_type for t in trips),
                         key=lambda x: [t.trip_type for t in trips].count(x))
                     if trips else "—")
    return render_template("dashboard.html",
        user=user, trips=trips,
        total_budget=total_budget, destinations=destinations, fav_type=fav_type)


@app.route("/trip/<share_id>")
def view_shared_trip(share_id):
    trip = SavedTrip.query.filter_by(share_id=share_id).first_or_404()
    plan = json.loads(trip.plan_json) if trip.plan_json else []
    return render_template("shared_trip.html", trip=trip, plan=plan)


# ══════════════════════════════════════════════════════════════
#  API ROUTES
# ══════════════════════════════════════════════════════════════
@app.route("/generate", methods=["POST"])
@limiter.limit("10 per minute")
def generate():
    data       = request.json or {}
    city_list  = [c.strip() for c in data.get("destination", "").split(",") if c.strip()]
    total_days = int(data.get("days", 3))
    budget     = int(data.get("budget", 25000))
    trip_type  = data.get("trip_type", "Solo")

    if not city_list:
        return jsonify({"error": "Destination required"}), 400

    result = []
    if len(city_list) == 1:
        city = city_list[0]
        ai   = generate_with_ai(city, total_days, budget, trip_type)
        result.append(ai if ai else generate_static_fallback(city, total_days, budget, trip_type))
    else:
        num_cities    = len(city_list)
        days_per_city = total_days // num_cities
        extra_days    = total_days % num_cities
        for i, city in enumerate(city_list):
            city_days = days_per_city + (1 if i < extra_days else 0)
            ai        = generate_with_ai(city, city_days, budget, trip_type)
            result.append(ai if ai else generate_static_fallback(city, city_days, budget, trip_type))

    return jsonify(result)


@app.route("/api/weather")
def proxy_weather():
    """Server-side weather proxy — avoids browser CORS issues."""
    city = request.args.get("city", "")
    if not city:
        return jsonify({"error": "city required"}), 400
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "VoyagerAI/1.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read().decode())
        cur = data["current_condition"][0]
        return jsonify({
            "tempC":    cur["temp_C"],
            "desc":     cur["weatherDesc"][0]["value"],
            "humidity": cur["humidity"],
            "feelsLike": cur["FeelsLikeC"],
            "windKmph": cur["windspeedKmph"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cities")
def api_cities():
    """Autocomplete cities from cities.json."""
    q = request.args.get("q", "").lower()
    if not q or not static_cities:
        return jsonify([])
    cities = static_cities if isinstance(static_cities, list) else list(static_cities.keys())
    matches = [c for c in cities if q in c.lower()][:8]
    return jsonify(matches)


@app.route("/save-trip", methods=["POST"])
def save_trip():
    data     = request.json or {}
    share_id = str(uuid.uuid4())[:10]
    user_id  = session.get("user_id")

    trip = SavedTrip(
        user_id=user_id, share_id=share_id,
        destination=data.get("destination", ""),
        days=data.get("days"), budget=data.get("budget"),
        trip_type=data.get("trip_type"),
        plan_json=json.dumps(data.get("plan", []))
    )
    db.session.add(trip)
    db.session.commit()
    return jsonify({"share_id": share_id,
                    "share_url": request.host_url + "trip/" + share_id})


@app.route("/delete-trip/<int:trip_id>", methods=["DELETE"])
@login_required
def delete_trip(trip_id):
    trip = SavedTrip.query.get_or_404(trip_id)
    if trip.user_id != session.get("user_id"):
        abort(403)
    db.session.delete(trip)
    db.session.commit()
    return jsonify({"status": "deleted"})


@app.route("/email-itinerary", methods=["POST"])
@limiter.limit("5 per minute")
def email_itinerary():
    data        = request.json or {}
    to_email    = data.get("email", "").strip()
    destination = data.get("destination", "")
    plan_data   = data.get("plan", [])

    if not to_email:
        return jsonify({"error": "Email required"}), 400
    try:
        msg      = Message(f"Your Voyager Itinerary — {destination}", recipients=[to_email])
        msg.html = render_template("email_itinerary.html",
                                   destination=destination, plan=plan_data,
                                   year=datetime.utcnow().year)
        mail.send(msg)
        return jsonify({"status": "sent"})
    except Exception as e:
        print(f"[MAIL ERROR] {e}")
        return jsonify({"error": "Mail not configured. Add MAIL_* keys to .env"}), 500


# ══════════════════════════════════════════════════════════════
#  ERROR HANDLERS
# ══════════════════════════════════════════════════════════════
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "Too many requests — please wait a moment."}), 429

@app.errorhandler(500)
def server_error(e):
    return render_template("404.html", error=str(e)), 500


import urllib.parse  # make sure this is imported

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 Voyager AI starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)