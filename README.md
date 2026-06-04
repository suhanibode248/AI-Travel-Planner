# AI Smart Eco Travel Planner

AI Smart Eco Travel Planner is a Streamlit app that creates travel itineraries from a destination, trip duration, budget, and trip type. It can use OpenRouter for AI-generated plans and falls back to local static data when no API key is configured.

---

## Features

- Streamlit-only deployment entry point: `streamlit_app.py`
- Login and registration with SQLite-backed users
- AI-generated itinerary support through OpenRouter
- Static fallback itinerary data for demos without an API key
- Saved trips and shareable trip IDs
- Optional email itinerary sending through SMTP secrets

---

## Local Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

---

## Streamlit Cloud Deployment

When creating the Streamlit Cloud app, set:

```text
Main file path: streamlit_app.py
```

Add this secret in Streamlit Cloud if you want AI generation:

```toml
OPENROUTER_API_KEY = "your_openrouter_api_key"
```

Optional email secrets:

```toml
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = "587"
MAIL_USE_TLS = "True"
MAIL_USERNAME = "your_email@gmail.com"
MAIL_PASSWORD = "your_email_app_password"
MAIL_DEFAULT_SENDER = "your_email@gmail.com"
```

Do not commit `.env` or `.streamlit/secrets.toml`.

---

## Limitations

- SQLite data on Streamlit Cloud is suitable for demos, but it is ephemeral and not ideal for production persistence.
- AI generation requires an internet connection and a valid OpenRouter API key.
- Email sending requires valid SMTP credentials.

---

## Future Scope

- Add more destinations and richer static fallback data
- Move persistence to a hosted database
- Add booking integrations
- Add real-time weather and map integrations
