
import json
import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/weather", tags=["Weather"])
# India uses a fixed UTC+05:30 offset (no daylight-saving transition). Using
# a fixed offset also works on Windows Python installs without a tzdata package.
INDIA_TZ = timezone(timedelta(hours=5, minutes=30), "IST")
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def fetch_json(url: str, params: dict):
    request_url = f"{url}?{urlencode(params)}"

    try:
        with urlopen(request_url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, OSError):
        raise HTTPException(
            status_code=502,
            detail="Weather service is temporarily unavailable."
        )


@router.get("")
def get_weather(city: str = Query(default="Solapur", min_length=2, max_length=80)):
    location = fetch_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json",
        },
    )

    results = location.get("results", [])
    if not results:
        raise HTTPException(status_code=404, detail="City not found.")

    place = results[0]

    weather = fetch_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "apparent_temperature,is_day,precipitation,rain,"
                "showers,snowfall,weather_code,cloud_cover,"
                "wind_speed_10m,wind_direction_10m"
            ),
            "timezone": "auto",
        },
    )

    current = weather.get("current")
    if not current:
        raise HTTPException(
            status_code=502,
            detail="Current weather data is unavailable."
        )

    code = current["weather_code"]
    rain = current.get("rain", 0) or 0
    showers = current.get("showers", 0) or 0

    if code in (95, 96, 99):
        risk, alert = "high", "Thunderstorm warning: use caution."
    elif code in (65, 67, 82) or rain + showers >= 7.5:
        risk, alert = "high", "Heavy rain risk: roads may be slippery."
    elif code in (51, 53, 55, 61, 63, 66, 80, 81) or rain + showers > 0:
        risk, alert = "moderate", "Rain detected: drive carefully."
    elif code in (45, 48):
        risk, alert = "moderate", "Fog conditions: visibility may be reduced."
    else:
        risk, alert = "low", "No major weather hazard detected by this rule set."

    return {
        "city": place["name"],
        "country": place.get("country"),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "timezone": weather.get("timezone"),
        "current": current,
        "weather_risk": risk,
        "road_alert": alert,
        "source": "Open-Meteo",
        "note": (
            "Weather-based advisory only. This does not confirm "
            "actual road flooding, closures, or road conditions."
        ),
    }


def geocode_place(name: str):
    location = fetch_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {
            "name": name,
            "count": 1,
            "language": "en",
            "format": "json",
            "countryCode": "IN",
        },
    )
    results = location.get("results", [])
    if not results:
        raise HTTPException(status_code=404, detail=f"Could not find '{name}' in India.")
    return results[0]


def route_samples(coordinates, distance_meters: float, max_samples: int = 8):
    """Return evenly spaced [longitude, latitude] points along an OSRM route."""
    if not coordinates:
        raise HTTPException(status_code=502, detail="Routing service returned no route geometry.")

    # OSRM's route distance is used for arrival estimates; cumulative straight
    # line segment lengths are enough to distribute forecast samples.
    segment_lengths = []
    cumulative = [0.0]
    for left, right in zip(coordinates, coordinates[1:]):
        lon1, lat1 = left
        lon2, lat2 = right
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        haversine = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        length = 6371000 * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
        segment_lengths.append(length)
        cumulative.append(cumulative[-1] + length)

    geometry_length = cumulative[-1]
    if geometry_length <= 0:
        return [{"fraction": 0.0, "distance_km": 0.0, "coordinate": coordinates[0]}]

    sample_count = max(3, min(max_samples, math.ceil(distance_meters / 15000) + 1))
    samples = []
    for sample_index in range(sample_count):
        fraction = sample_index / (sample_count - 1)
        target = geometry_length * fraction
        segment_index = next(
            (index for index, end in enumerate(cumulative[1:]) if end >= target),
            len(segment_lengths) - 1,
        )
        segment_start = cumulative[segment_index]
        segment_length = segment_lengths[segment_index]
        segment_fraction = 0 if segment_length == 0 else (target - segment_start) / segment_length
        start = coordinates[segment_index]
        end = coordinates[segment_index + 1]
        coordinate = [
            start[0] + (end[0] - start[0]) * segment_fraction,
            start[1] + (end[1] - start[1]) * segment_fraction,
        ]
        samples.append({
            "fraction": fraction,
            "distance_km": round(distance_meters * fraction / 1000, 1),
            "coordinate": coordinate,
        })
    return samples


@router.get("/route")
def get_route_weather(
    origin: str = Query(default="Sangola", min_length=2, max_length=100),
    destination: str = Query(default="Solapur", min_length=2, max_length=100),
    departure: str = Query(default="", max_length=40),
):
    origin_place = geocode_place(origin)
    destination_place = geocode_place(destination)

    # Coordinates are longitude,latitude for OSRM's URL path.
    route_url = (
        f"{OSRM_URL}/"
        f"{origin_place['longitude']},{origin_place['latitude']};"
        f"{destination_place['longitude']},{destination_place['latitude']}"
    )
    route_data = fetch_json(
        route_url,
        {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false",
            "alternatives": 2,
        },
    )
    routes = route_data.get("routes", [])
    if route_data.get("code") != "Ok" or not routes:
        raise HTTPException(status_code=502, detail="No drivable route was found between these locations.")
    route_candidates = []
    combined_samples = []
    for route_index, road_route in enumerate(routes[:3]):
        distance_meters = float(road_route.get("distance", 0))
        duration_seconds = float(road_route.get("duration", 0))
        coordinates = road_route.get("geometry", {}).get("coordinates", [])
        samples = route_samples(coordinates, distance_meters)
        route_candidates.append({
            "route": road_route,
            "distance_meters": distance_meters,
            "duration_seconds": duration_seconds,
            "coordinates": coordinates,
            "samples": samples,
            "points": [],
        })
        combined_samples.extend(
            (route_index, sample)
            for sample in samples
        )

    try:
        departure_time = (
            datetime.fromisoformat(departure.replace("Z", "+00:00"))
            if departure
            else datetime.now(INDIA_TZ)
        )
        if departure_time.tzinfo is None:
            departure_time = departure_time.replace(tzinfo=INDIA_TZ)
        departure_time = departure_time.astimezone(INDIA_TZ)
    except ValueError:
        raise HTTPException(status_code=400, detail="Departure time must be a valid ISO date and time.")

    now = datetime.now(INDIA_TZ)
    if departure_time < now - timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Choose a departure time in the present or future.")
    if departure_time + timedelta(seconds=route_candidates[0]["duration_seconds"]) > now + timedelta(days=7):
        raise HTTPException(status_code=400, detail="Choose a departure within the next 7 days.")

    latitudes = ",".join(
        f"{sample['coordinate'][1]:.5f}"
        for _, sample in combined_samples
    )
    longitudes = ",".join(
        f"{sample['coordinate'][0]:.5f}"
        for _, sample in combined_samples
    )
    forecast = fetch_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": latitudes,
            "longitude": longitudes,
            "hourly": "precipitation_probability,precipitation,rain,showers,weather_code,wind_speed_10m,visibility",
            "forecast_days": 7,
            "timezone": "Asia/Kolkata",
        },
    )
    forecasts = forecast if isinstance(forecast, list) else [forecast]
    if len(forecasts) != len(combined_samples):
        raise HTTPException(status_code=502, detail="Weather service did not return forecasts for every route point.")

    for index, ((route_index, sample), point_forecast) in enumerate(zip(combined_samples, forecasts)):
        candidate = route_candidates[route_index]
        hourly = point_forecast.get("hourly", {})
        times = hourly.get("time", [])
        if not times:
            continue
        arrival = departure_time + timedelta(seconds=candidate["duration_seconds"] * sample["fraction"])
        forecast_times = [datetime.fromisoformat(value).replace(tzinfo=INDIA_TZ) for value in times]
        weather_index = min(range(len(forecast_times)), key=lambda i: abs(forecast_times[i] - arrival))
        weather_time = forecast_times[weather_index]
        if abs((weather_time - arrival).total_seconds()) > 5400:
            raise HTTPException(status_code=422, detail="Weather forecast is unavailable for the selected travel time.")

        def at_hour(variable, fallback=0):
            values = hourly.get(variable, [])
            return values[weather_index] if weather_index < len(values) and values[weather_index] is not None else fallback

        rain_mm = float(at_hour("precipitation", 0) or 0)
        rain_probability = int(at_hour("precipitation_probability", 0) or 0)
        weather_code = int(at_hour("weather_code", 0) or 0)
        wind_speed = round(float(at_hour("wind_speed_10m", 0) or 0), 1)
        visibility_m = int(at_hour("visibility", 10000) or 10000)
        heavy_rain = weather_code in (65, 67, 82, 95, 96, 99) or rain_mm >= 7.5
        moderate_rain = weather_code in (51, 53, 55, 61, 63, 66, 80, 81) or rain_mm > 0 or rain_probability >= 40
        risk = "high" if heavy_rain else "moderate" if moderate_rain else "low"
        if heavy_rain:
            road_condition = "High water risk"
            road_advice = "Heavy rain may cause water accumulation and slippery surfaces. Avoid flooded sections; flooding is not directly observed by this forecast."
            road_condition_risk = "high"
        elif moderate_rain:
            road_condition = "Wet / slippery risk"
            road_advice = "Rain may make the road surface slick and reduce braking grip. Slow down and increase following distance."
            road_condition_risk = "moderate"
        elif visibility_m < 1000:
            road_condition = "Low visibility"
            road_advice = "Forecast visibility is reduced. Use lights and drive cautiously."
            road_condition_risk = "moderate"
        elif wind_speed >= 50:
            road_condition = "Strong wind"
            road_advice = "Strong winds may affect high-sided vehicles and motorcycles."
            road_condition_risk = "moderate"
        else:
            road_condition = "Likely dry"
            road_advice = "No significant rain or visibility hazard is forecast at this checkpoint."
            road_condition_risk = "low"
        if weather_code in (95, 96, 99):
            alert = "Thunderstorm risk along this route point."
        elif heavy_rain:
            alert = "Heavy rainfall forecast; expect slippery roads and reduced visibility."
        elif moderate_rain:
            alert = "Rain is possible; allow extra travel time."
        else:
            alert = "No significant rain is forecast at this route point."

        candidate["points"].append({
            "index": len(candidate["points"]) + 1,
            "distance_km": sample["distance_km"],
            "coordinate": sample["coordinate"],
            "arrival_time": arrival.isoformat(),
            "forecast_time": weather_time.isoformat(),
            "precipitation_mm": round(rain_mm, 1),
            "precipitation_probability": rain_probability,
            "wind_speed_kmh": wind_speed,
            "visibility_m": visibility_m,
            "weather_code": weather_code,
            "risk": risk,
            "heavy_rain": heavy_rain,
            "road_condition": road_condition,
            "road_condition_risk": road_condition_risk,
            "road_advice": road_advice,
            "alert": alert,
        })

    for candidate in route_candidates:
        points = candidate["points"]
        candidate["heavy_points"] = [point for point in points if point["heavy_rain"]]
        candidate["moderate_points"] = [point for point in points if point["risk"] == "moderate"]
        candidate["weather_risk"] = (
            "high" if candidate["heavy_points"]
            else "moderate" if candidate["moderate_points"]
            else "low"
        )

    primary = route_candidates[0]
    safest_candidate = min(
        enumerate(route_candidates),
        key=lambda item: (
            len(item[1]["heavy_points"]),
            len(item[1]["moderate_points"]),
            item[1]["duration_seconds"],
        ),
    )
    safer_alternative = None
    if safest_candidate[0] > 0:
        alternative_candidate = safest_candidate[1]
        primary_risk_key = (
            len(primary["heavy_points"]),
            len(primary["moderate_points"]),
        )
        alternative_risk_key = (
            len(alternative_candidate["heavy_points"]),
            len(alternative_candidate["moderate_points"]),
        )
        if alternative_risk_key < primary_risk_key:
            safer_alternative = alternative_candidate

    heavy_points = primary["heavy_points"]
    moderate_points = primary["moderate_points"]
    overall_risk = primary["weather_risk"]

    def route_summary(candidate):
        return {
            "distance_km": round(candidate["distance_meters"] / 1000, 1),
            "duration_minutes": round(candidate["duration_seconds"] / 60),
            "geometry": candidate["coordinates"],
            "points": candidate["points"],
            "weather_risk": candidate["weather_risk"],
            "heavy_rain_alert": bool(candidate["heavy_points"]),
            "alerts": [point for point in candidate["points"] if point["risk"] != "low"],
        }

    return {
        "origin": {
            "name": origin_place["name"],
            "region": origin_place.get("admin1"),
            "latitude": origin_place["latitude"],
            "longitude": origin_place["longitude"],
        },
        "destination": {
            "name": destination_place["name"],
            "region": destination_place.get("admin1"),
            "latitude": destination_place["latitude"],
            "longitude": destination_place["longitude"],
        },
        "departure_time": departure_time.isoformat(),
        "distance_km": round(primary["distance_meters"] / 1000, 1),
        "duration_minutes": round(primary["duration_seconds"] / 60),
        "geometry": primary["coordinates"],
        "points": primary["points"],
        "weather_risk": overall_risk,
        "road_condition_summary": (
            "High water risk" if any(point["road_condition_risk"] == "high" for point in primary["points"])
            else "Caution advised" if any(point["road_condition_risk"] == "moderate" for point in primary["points"])
            else "Likely dry"
        ),
        "road_condition_risk": (
            "high" if any(point["road_condition_risk"] == "high" for point in primary["points"])
            else "moderate" if any(point["road_condition_risk"] == "moderate" for point in primary["points"])
            else "low"
        ),
        "heavy_rain_alert": bool(heavy_points),
        "alerts": [point for point in primary["points"] if point["risk"] != "low"],
        "alternate_route": route_summary(safer_alternative) if safer_alternative else None,
        "source": "OpenStreetMap routing + Open-Meteo forecast",
        "note": "Forecasts are sampled at route points near estimated arrival times. Weather forecasts are advisory and do not confirm road flooding, closures, or actual road safety.",
    }
