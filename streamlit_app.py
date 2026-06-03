import streamlit as st
import uuid
import json
from dotenv import load_dotenv

# Load env variables (for local dev)
load_dotenv()

# Pull secrets from st.secrets if deployed on Streamlit Cloud
import os
try:
    for key in ["OPENROUTER_API_KEY", "MAIL_SERVER", "MAIL_PORT", "MAIL_USE_TLS", "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_DEFAULT_SENDER"]:
        if key in st.secrets:
            os.environ[key] = str(st.secrets[key])
except FileNotFoundError:
    pass # Locally, we use .env instead of secrets.toml
except Exception:
    pass

from db import init_db, get_db, User, SavedTrip, hash_password, check_password
from ai_service import generate_with_ai, generate_static_fallback
from email_service import send_itinerary_email

st.set_page_config(page_title="Voyager AI", page_icon="✈️", layout="wide")

# Initialize database
init_db()

# Session State Initialization
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "view" not in st.session_state:
    st.session_state.view = "login"

def go_to(view_name):
    st.session_state.view = view_name
    st.rerun()

def login_view():
    st.title("Welcome to Voyager AI")
    st.subheader("Sign In")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign In")
        
        if submitted:
            with get_db() as db:
                user = db.query(User).filter_by(username=username).first()
                if user and check_password(password, user.password):
                    st.session_state.user_id = user.id
                    st.session_state.name = user.name
                    st.success("Logged in successfully!")
                    go_to("home")
                else:
                    st.error("Invalid username or password.")
                    
    st.markdown("---")
    st.subheader("Register")
    with st.form("register_form"):
        new_name = st.text_input("Full Name")
        new_email = st.text_input("Email")
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        reg_submitted = st.form_submit_button("Create Account")
        
        if reg_submitted:
            if not all([new_name, new_email, new_username, new_password]):
                st.error("All fields are required.")
            else:
                with get_db() as db:
                    if db.query(User).filter_by(username=new_username).first():
                        st.error("Username already taken.")
                    elif db.query(User).filter_by(email=new_email).first():
                        st.error("Email already registered.")
                    else:
                        hashed = hash_password(new_password)
                        user = User(username=new_username, email=new_email, name=new_name, password=hashed)
                        db.add(user)
                        db.commit()
                        st.session_state.user_id = user.id
                        st.session_state.name = new_name
                        st.success("Account created!")
                        go_to("home")

    st.markdown("---")
    if st.button("Continue as Guest"):
        st.session_state.user_id = None
        go_to("home")

def render_navbar():
    col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
    with col1:
        st.markdown("### ✈️ Voyager AI")
    with col2:
        if st.button("Home"):
            go_to("home")
    with col3:
        if st.session_state.user_id:
            if st.button("Dashboard"):
                go_to("dashboard")
        else:
            if st.button("Login"):
                go_to("login")
    with col4:
        if st.session_state.user_id:
            if st.button("Logout"):
                st.session_state.user_id = None
                go_to("login")

def render_itinerary(plan_data):
    for city_plan in plan_data:
        st.header(city_plan.get("city", "Destination"))
        st.write(city_plan.get("plan", ""))
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Places to Visit")
            for place in city_plan.get("places", []):
                st.write(f"- {place.get('name')}")
            
            st.subheader("Transport")
            cabs = city_plan.get("transport", {}).get("cabs", [])
            for cab in cabs:
                st.markdown(f"- [{cab.get('name')}]({cab.get('link')})")
        with c2:
            st.subheader("Hotels")
            for hotel in city_plan.get("hotels", []):
                st.markdown(f"- **{hotel.get('type').title()}**: [{hotel.get('name')}]({hotel.get('link')})")
            
            st.subheader("Food")
            st.write("**Street Food:**", ", ".join(city_plan.get("food", {}).get("street_food", [])))
            st.write("**Restaurants:**")
            for rest in city_plan.get("food", {}).get("restaurants", []):
                st.markdown(f"- [{rest.get('name')}]({rest.get('link')})")

def home_view():
    render_navbar()
    st.title("Plan Your Trip")
    
    with st.form("planner_form"):
        destination = st.text_input("Destination (comma separated for multiple)")
        days = st.number_input("Number of Days", min_value=1, max_value=30, value=3)
        budget = st.number_input("Total Budget (₹)", min_value=500, value=15000, step=1000)
        trip_type = st.selectbox("Trip Type", ["Solo", "Family", "Friends", "Honeymoon"])
        submit = st.form_submit_button("Generate Itinerary")
        
    if submit and destination:
        with st.spinner("Generating itinerary..."):
            city_list = [c.strip() for c in destination.split(",")]
            result = []
            
            if len(city_list) == 1:
                city = city_list[0]
                ai = generate_with_ai(city, days, budget, trip_type)
                result.append(ai if ai else generate_static_fallback(city, days, budget, trip_type))
            else:
                num_cities = len(city_list)
                days_per_city = days // num_cities
                extra_days = days % num_cities
                for i, city in enumerate(city_list):
                    city_days = days_per_city + (1 if i < extra_days else 0)
                    ai = generate_with_ai(city, city_days, budget, trip_type)
                    result.append(ai if ai else generate_static_fallback(city, city_days, budget, trip_type))
            
            st.session_state.current_plan = result
            st.session_state.current_plan_meta = {
                "destination": destination,
                "days": days,
                "budget": budget,
                "trip_type": trip_type
            }

    if "current_plan" in st.session_state:
        st.markdown("---")
        render_itinerary(st.session_state.current_plan)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.user_id:
                if st.button("Save Trip"):
                    share_id = str(uuid.uuid4())[:10]
                    with get_db() as db:
                        meta = st.session_state.current_plan_meta
                        trip = SavedTrip(
                            user_id=st.session_state.user_id,
                            share_id=share_id,
                            destination=meta["destination"],
                            days=meta["days"],
                            budget=meta["budget"],
                            trip_type=meta["trip_type"],
                            plan_json=json.dumps(st.session_state.current_plan)
                        )
                        db.add(trip)
                        db.commit()
                        st.success(f"Trip saved! Share link: `/trip/{share_id}`")
            else:
                st.info("Log in to save this trip.")
        
        with col2:
            with st.form("email_form"):
                email = st.text_input("Email this itinerary to:")
                email_submit = st.form_submit_button("Send Email")
                if email_submit and email:
                    try:
                        send_itinerary_email(email, st.session_state.current_plan_meta["destination"], st.session_state.current_plan)
                        st.success("Email sent!")
                    except Exception as e:
                        st.error(f"Failed to send email: {e}")

def dashboard_view():
    render_navbar()
    if not st.session_state.user_id:
        st.error("Please sign in first.")
        return
    
    st.title("Your Dashboard")
    with get_db() as db:
        user = db.query(User).get(st.session_state.user_id)
        trips = db.query(SavedTrip).filter_by(user_id=user.id).order_by(SavedTrip.created_at.desc()).all()
        
        if not trips:
            st.info("You haven't saved any trips yet.")
        else:
            total_budget = sum(t.budget or 0 for t in trips)
            st.write(f"**Total Budget Planned:** ₹{total_budget}")
            
            for trip in trips:
                with st.expander(f"{trip.destination} - {trip.days} Days ({trip.trip_type})"):
                    st.write(f"**Budget:** ₹{trip.budget}")
                    st.write(f"**Saved on:** {trip.created_at.strftime('%Y-%m-%d')}")
                    st.write(f"**Share Code:** `{trip.share_id}`")
                    if st.button("View Details", key=f"view_{trip.id}"):
                        st.session_state.current_plan = json.loads(trip.plan_json)
                        st.session_state.current_plan_meta = {
                            "destination": trip.destination,
                            "days": trip.days,
                            "budget": trip.budget,
                            "trip_type": trip.trip_type
                        }
                        go_to("home")
                    if st.button("Delete Trip", key=f"del_{trip.id}"):
                        db.delete(trip)
                        db.commit()
                        st.rerun()

# Routing
if st.session_state.view == "login":
    login_view()
elif st.session_state.view == "home":
    home_view()
elif st.session_state.view == "dashboard":
    dashboard_view()