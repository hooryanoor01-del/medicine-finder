import json
import math
import os
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
USER_AGENT = os.getenv(
    "HTTP_USER_AGENT",
    "PakistanMedicineFinder/1.0 (educational project; contact: update-this@example.com)",
)
MEDICINES_FILE = Path(__file__).with_name("medicines.json")
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Approximate Pakistan bounds as a safeguard, not an official border polygon.
PAKISTAN = (23.4, 37.2, 60.7, 77.9)  # min lat, max lat, min lon, max lon


def in_pakistan(lat, lon):
    min_lat, max_lat, min_lon, max_lon = PAKISTAN
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def distance_km(lat1, lon1, lat2, lon2):
    radius = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def read_medicines():
    try:
        with MEDICINES_FILE.open(encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/medicines")
def medicine_search():
    query = request.args.get("q", "").strip().casefold()
    items = read_medicines()
    if query:
        items = [m for m in items if query in " ".join([
            m.get("name", ""), m.get("category", ""),
            *m.get("search_terms", []), *m.get("aliases", [])
        ]).casefold()]
    return jsonify({"medicines": items})


@app.get("/api/geocode")
def geocode():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify(error="Enter a city or area in Pakistan."), 400
    try:
        response = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "jsonv2", "addressdetails": 1,
                    "countrycodes": "pk", "limit": 1},
            headers={"User-Agent": USER_AGENT}, timeout=15,
        )
        response.raise_for_status()
        results = response.json()
    except (requests.RequestException, ValueError):
        return jsonify(error="Location search is temporarily unavailable."), 502
    if not results:
        return jsonify(error="No matching location found in Pakistan."), 404
    try:
        lat, lon = float(results[0]["lat"]), float(results[0]["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="The location service returned invalid coordinates."), 502
    if not in_pakistan(lat, lon):
        return jsonify(error="Please search for a location in Pakistan."), 400
    return jsonify(name=results[0].get("display_name", query), lat=lat, lon=lon)


@app.get("/api/pharmacies")
def pharmacies():
    try:
        lat = float(request.args.get("lat", ""))
        lon = float(request.args.get("lon", ""))
        radius = max(1000, min(int(request.args.get("radius", "5000")), 50000))
    except (TypeError, ValueError):
        return jsonify(error="Valid coordinates and search radius are required."), 400
    if not in_pakistan(lat, lon):
        return jsonify(error="Search coordinates must be in Pakistan."), 400

    query = f"""[out:json][timeout:25];
    (node[\"amenity\"=\"pharmacy\"](around:{radius},{lat},{lon});
     way[\"amenity\"=\"pharmacy\"](around:{radius},{lat},{lon});
     relation[\"amenity\"=\"pharmacy\"](around:{radius},{lat},{lon}););
    out center tags;"""
    try:
        response = requests.post(
            OVERPASS_URL, data={"data": query},
            headers={"User-Agent": USER_AGENT}, timeout=35,
        )
        response.raise_for_status()
        elements = response.json().get("elements", [])
    except (requests.RequestException, ValueError):
        return jsonify(error="The pharmacy map service is busy. Please try again shortly."), 502

    results = []
    for element in elements:
        tags = element.get("tags", {})
        point = element.get("center", element)
        try:
            p_lat, p_lon = float(point["lat"]), float(point["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        if not in_pakistan(p_lat, p_lon):
            continue
        address = ", ".join(filter(None, [
            tags.get("addr:street"), tags.get("addr:suburb"), tags.get("addr:city")
        ]))
        results.append({
            "id": f"{element.get('type', 'item')}/{element.get('id', '')}",
            "name": tags.get("name") or tags.get("brand") or "Pharmacy",
            "lat": p_lat, "lon": p_lon, "address": address,
            "phone": tags.get("phone") or tags.get("contact:phone") or "",
            "opening_hours": tags.get("opening_hours", ""),
            "distance_km": round(distance_km(lat, lon, p_lat, p_lon), 1),
        })
    results.sort(key=lambda item: item["distance_km"])
    return jsonify(pharmacies=results, radius_m=radius)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
