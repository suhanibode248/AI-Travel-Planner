import os, json, re
import requests as http_requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL   = "google/gemini-flash-1.5"

def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}

# Fallback static data
static_places      = _load_json("data/places.json")
static_hotels      = _load_json("data/hotels.json")
static_restaurants = _load_json("data/restaurants.json")
static_transport   = _load_json("data/transport.json")

def generate_with_ai(destination, days, budget, trip_type):
    """Call OpenRouter (Gemini Flash) to generate a full itinerary. Returns parsed dict or None."""
    if not OPENROUTER_API_KEY:
        return None
    
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
      {{"name": "Ola",   "link": "https://www.olacabs.com"}},
      {{"name": "Uber",  "link": "https://www.uber.com/in/en/"}},
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
        response = http_requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": OPENROUTER_MODEL,
                "max_tokens": 2000,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$',     '', text)
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
    days = int(days)
    per_day     = max(1, len(city_places) // days) if city_places else 1
    lines, idx  = [], 0

    for d in range(days):
        chunk = city_places[idx:idx + per_day]
        idx  += per_day
        if chunk:
            text = f"{prefix} {', '.join(p['name'] for p in chunk)}"
        else:
            act  = fallback[d % len(fallback)]
            text = {"Friends":  f"Enjoy {act} with friends",
                    "Family":   f"Family time: {act}",
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
