"""
╔══════════════════════════════════════════════════════════════╗
║  VOYAGER AI — app.py  (v3 — 10/10 Edition)                  ║
║  Features:                                                   ║
║  • Claude AI itinerary generation                            ║
║  • SQLite + bcrypt auth (register / login / logout)          ║
║  • Saved trips (per user)                                    ║
║  • Shareable trip links (/trip/<share_id>)                   ║
║  • User dashboard                                            ║
║  • Email itinerary (Flask-Mail / SendGrid)                   ║
║  • Rate limiting on /generate                                ║
║  • .env for secrets                                          ║
╚══════════════════════════════════════════════════════════════╝

SETUP:
  pip install flask flask-sqlalchemy flask-bcrypt flask-mail \
              flask-limiter anthropic python-dotenv

Create a  .env  file beside app.py:
  SECRET_KEY=change-me-in-production
  ANTHROPIC_API_KEY=sk-ant-...
  MAIL_SERVER=smtp.gmail.com
  MAIL_PORT=587
  MAIL_USE_TLS=True
  MAIL_USERNAME=you@gmail.com
  MAIL_PASSWORD=your-app-password
  MAIL_DEFAULT_SENDER=you@gmail.com
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

# ── App setup ──────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "voyager-dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///voyager.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Mail config
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

# Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

# ── Fallback static data (used if AI is unavailable) ───────────
def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}

static_places     = _load_json("data/places.json")
static_hotels     = _load_json("data/hotels.json")
static_restaurants= _load_json("data/restaurants.json")
static_transport  = _load_json("data/transport.json")


# ══════════════════════════════════════════════════════════════
#  DATABASE MODELS
# ══════════════════════════════════════════════════════════════
class User(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    name       = db.Column(db.String(100), nullable=False)
    password   = db.Column(db.String(200), nullable=False)   # bcrypt hash
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
    plan_json   = db.Column(db.Text)     # full AI JSON response
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)


# Create tables on first run
with app.app_context():
    db.create_all()
    # Seed admin user if not exists
    if not User.query.filter_by(username="admin").first():
        hashed = bcrypt.generate_password_hash("admin123").decode("utf-8")
        db.session.add(User(username="admin", email="admin@voyager.ai",
                            name="Admin", password=hashed))
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
#  AI ITINERARY GENERATION
# ══════════════════════════════════════════════════════════════
def generate_with_ai(destination, days, budget, trip_type):
    """Call Claude to generate a full itinerary. Returns parsed dict or None."""
    prompt = f"""You are an expert Indian travel planner. Create a detailed {days}-day itinerary for {destination}.
Trip type: {trip_type}
Total budget: ₹{budget}

Return ONLY valid JSON — no markdown, no explanation, just the JSON object:
{{
  "city": "{destination}",
  "plan": "Day 1: Morning visit to ..., afternoon ..., evening ...\\nDay 2: ...",
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
      {{"name": "Restaurant Name", "link": "https://www.zomato.com/search?q={destination}"}},
      {{"name": "Restaurant Name", "link": "https://www.zomato.com/search?q={destination}"}}
    ]
  }},
  "transport": {{
    "cabs": [
      {{"name": "Ola",  "link": "https://www.olacabs.com"}},
      {{"name": "Uber", "link": "https://www.uber.com/in/en/"}},
      {{"name": "Rapido","link": "https://rapido.bike"}}
    ]
  }},
  "tips": [
    "Useful travel tip 1",
    "Useful travel tip 2",
    "Useful travel tip 3"
  ],
  "similar": ["Nearby City 1", "Nearby City 2", "Nearby City 3"]
}}

Make plan, places, hotels, food realistic and specific to {destination}.
For {trip_type} trips, tailor the activities appropriately.
Budget ₹{budget}: {"budget hotels and street food" if int(budget) < 10000 else "mid-range hotels" if int(budget) < 50000 else "luxury options"}.
"""
    try:
        response = anthropic_client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()
        # Strip any accidental markdown fences
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text)
    except Exception as e:
        print(f"AI generation failed: {e}")
        return None


def generate_static_fallback(city, days, budget, trip_type):
    """Return a static-data plan when AI is unavailable."""
    city_places = static_places.get(city, [])
    fallback    = ["Shopping", "Leisure & Relaxation", "Local exploration",
                   "Cafe hopping", "Street food experience"]
    prefix      = {"Solo": "Explore", "Family": "Visit family-friendly spots at",
                   "Friends": "Enjoy with friends at", "Honeymoon": "Romantic visit to"}.get(trip_type, "Visit")
    per_day     = max(1, len(city_places) // days) if city_places else 1
    lines, idx  = [], 0

    for d in range(days):
        chunk = city_places[idx:idx + per_day]
        idx  += per_day
        if chunk:
            text = f"{prefix} {', '.join(p['name'] for p in chunk)}"
        else:
            act  = fallback[d % len(fallback)]
            text = {"Friends": f"Enjoy {act} with friends",
                    "Family":  f"Family time: {act}",
                    "Honeymoon": f"Romantic {act}"}.get(trip_type, f"{act} and relaxation")
        lines.append(f"Day {d + 1}: {text}")

    city_hotels = static_hotels.get(city, [])
    if int(budget) < 5000:
        city_hotels = [h for h in city_hotels if h.get("type") == "budget"]

    return {
        "city":      city,
        "plan":      "\n".join(lines),
        "places":    city_places,
        "hotels":    city_hotels,
        "food":      static_restaurants.get(city, {}),
        "transport": static_transport.get(city, {}),
        "tips":      [],
        "similar":   []
    }


# ══════════════════════════════════════════════════════════════
#  ROUTES — AUTH
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
    user     = User.query.filter_by(username=username).first()

    if user and bcrypt.check_password_hash(user.password, password):
        session["user_id"] = user.id
        session["name"]    = user.name
        return redirect(url_for("home"))
    return redirect(url_for("login_page") + "?error=Invalid+username+or+password")


@app.route("/register", methods=["POST"])
def handle_register():
    fullname = request.form.get("fullname", "").strip()
    email    = request.form.get("email",    "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not all([fullname, email, username, password]):
        return redirect(url_for("login_page") + "?error=All+fields+are+required")
    if User.query.filter_by(username=username).first():
        return redirect(url_for("login_page") + "?error=Username+already+taken")
    if User.query.filter_by(email=email).first():
        return redirect(url_for("login_page") + "?error=Email+already+registered")

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user   = User(username=username, email=email, name=fullname, password=hashed)
    db.session.add(user)
    db.session.commit()
    session["user_id"] = user.id
    session["name"]    = fullname
    return redirect(url_for("home") + "?success=Welcome+to+Voyager!")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page") + "?success=Signed+out+successfully")


# ══════════════════════════════════════════════════════════════
#  ROUTES — MAIN APP
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
    trips = SavedTrip.query.filter_by(user_id=user.id).order_by(SavedTrip.created_at.desc()).all()

    # Stats
    total_budget  = sum(t.budget or 0 for t in trips)
    destinations  = list({t.destination for t in trips})
    fav_type      = max(set(t.trip_type for t in trips), key=lambda x: [t.trip_type for t in trips].count(x)) if trips else "—"

    return render_template("dashboard.html",
        user=user, trips=trips,
        total_budget=total_budget,
        destinations=destinations,
        fav_type=fav_type
    )


@app.route("/trip/<share_id>")
def view_shared_trip(share_id):
    trip = SavedTrip.query.filter_by(share_id=share_id).first_or_404()
    plan = json.loads(trip.plan_json) if trip.plan_json else []
    return render_template("shared_trip.html", trip=trip, plan=plan)


# ══════════════════════════════════════════════════════════════
#  ROUTES — API
# ══════════════════════════════════════════════════════════════
@app.route("/generate", methods=["POST"])
@limiter.limit("10 per minute")
def generate():
    data       = request.json
    city_list  = [c.strip() for c in data["destination"].split(",")]
    total_days = int(data["days"])
    budget     = int(data["budget"])
    trip_type  = data["trip_type"]
    result     = []

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


@app.route("/save-trip", methods=["POST"])
def save_trip():
    data        = request.json
    share_id    = str(uuid.uuid4())[:10]
    user_id     = session.get("user_id")

    trip = SavedTrip(
        user_id     = user_id,
        share_id    = share_id,
        destination = data.get("destination"),
        days        = data.get("days"),
        budget      = data.get("budget"),
        trip_type   = data.get("trip_type"),
        plan_json   = json.dumps(data.get("plan"))
    )
    db.session.add(trip)
    db.session.commit()

    share_url = request.host_url + "trip/" + share_id
    return jsonify({"share_id": share_id, "share_url": share_url})


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
    data        = request.json
    to_email    = data.get("email", "").strip()
    destination = data.get("destination", "")
    plan_data   = data.get("plan", [])

    if not to_email:
        return jsonify({"error": "Email required"}), 400

    try:
        msg      = Message(f"Your Voyager Itinerary — {destination}", recipients=[to_email])
        msg.html = render_template("email_itinerary.html",
                                   destination=destination,
                                   plan=plan_data,
                                   year=datetime.utcnow().year)
        mail.send(msg)
        return jsonify({"status": "sent"})
    except Exception as e:
        print(f"Mail error: {e}")
        return jsonify({"error": "Mail not configured. Add MAIL_* keys to .env"}), 500


# ══════════════════════════════════════════════════════════════
#  ERROR PAGES
# ══════════════════════════════════════════════════════════════
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "Too many requests — please wait a moment."}), 429


# ══════════════════════════════════════════════════════════════
#  RUN
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("🚀 Voyager AI v3 starting…")
    app.run(debug=True)