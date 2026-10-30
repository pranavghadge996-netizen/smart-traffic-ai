
import React, { useEffect, useMemo, useState } from "react";
import {
  CircleMarker,
  MapContainer,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { saveRouteWeather } from "../utils/routeWeatherAlerts";

const API = "http://127.0.0.1:8000/api/weather/route";
const INDIA_TIMEZONE_OFFSET = new Date().getTimezoneOffset() * 60000;
const INITIAL_DEPARTURE = new Date(Date.now() - INDIA_TIMEZONE_OFFSET)
  .toISOString()
  .slice(0, 16);

const RISK_COLORS = {
  high: "#fb6474",
  moderate: "#f4bd4f",
  low: "#38df9a",
};

function formatTime(value) {
  return new Date(value).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });
}

function FitRoute({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length > 1) map.fitBounds(positions, { padding: [30, 30] });
  }, [map, positions]);
  return null;
}

function RouteMap({ route, positions, alternatePositions, allRoutePositions }) {
  const center = positions[Math.floor(positions.length / 2)] || [17.7, 75.1];
  const routeColor = RISK_COLORS[route.weather_risk] || RISK_COLORS.low;

  return (
    <div className="route-weather-map">
      <MapContainer center={center} zoom={9} scrollWheelZoom className="route-weather-leaflet">
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitRoute positions={allRoutePositions} />
        <Polyline positions={positions} pathOptions={{ color: routeColor, weight: 6, opacity: 0.86 }} />
        {alternatePositions.length > 1 && (
          <Polyline
            positions={alternatePositions}
            pathOptions={{ color: "#38df9a", weight: 6, opacity: 0.9, dashArray: "10 10" }}
          />
        )}
        {route.points.map((point) => (
          <CircleMarker
            key={point.index}
            center={[point.coordinate[1], point.coordinate[0]]}
            radius={8}
            pathOptions={{
              color: "#07111c",
              weight: 2,
              fillColor: RISK_COLORS[point.risk] || RISK_COLORS.low,
              fillOpacity: 1,
            }}
          >
            <Popup>
              <strong>Route point {point.index}</strong><br />
              {point.distance_km} km from origin<br />
              {point.precipitation_mm} mm rain · {point.precipitation_probability}% chance<br />
              {formatTime(point.arrival_time)} estimated arrival
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <div className="route-map-legend">
        <span><i className="risk-dot low" /> Low rain risk</span>
        <span><i className="risk-dot moderate" /> Rain possible</span>
        <span><i className="risk-dot high" /> Heavy rain alert</span>
        {alternatePositions.length > 1 && <span><i className="risk-dot alternate" /> Lower-risk alternative</span>}
      </div>
    </div>
  );
}

export default function Weather() {
  const [origin, setOrigin] = useState("Sangola");
  const [destination, setDestination] = useState("Solapur");
  const [departure, setDeparture] = useState(INITIAL_DEPARTURE);
  const [route, setRoute] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [weatherPopup, setWeatherPopup] = useState(null);

  const positions = useMemo(
    () => (route?.geometry || []).map(([longitude, latitude]) => [latitude, longitude]),
    [route?.geometry]
  );
  const alternatePositions = useMemo(
    () => (route?.alternate_route?.geometry || []).map(([longitude, latitude]) => [latitude, longitude]),
    [route?.alternate_route?.geometry]
  );
  const allRoutePositions = useMemo(
    () => [...positions, ...alternatePositions],
    [positions, alternatePositions]
  );

  async function loadRoute(event) {
    event?.preventDefault();
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({ origin, destination, departure });
      const response = await fetch(`${API}?${params.toString()}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || `Route weather failed (${response.status}).`);
      setRoute(data);
      saveRouteWeather(data);
      if (data.weather_risk === "high" || data.weather_risk === "moderate") {
        setWeatherPopup({
          severity: data.weather_risk,
          route: `${data.origin.name} → ${data.destination.name}`,
          reason: data.heavy_rain_alert
            ? "Heavy rain is forecast at one or more route checkpoints."
            : "Rain or other adverse weather is forecast along this route.",
        });
      } else {
        setWeatherPopup(null);
      }
    } catch (err) {
      setRoute(null);
      setError(err.message || "Unable to load route weather.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRoute();
    // Load the default Sangola to Solapur forecast once when the page opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const highRiskPoints = route?.points.filter((point) => point.heavy_rain) || [];
  const moderateRiskPoints = route?.points.filter((point) => point.risk === "moderate") || [];

  return (
    <div className="page weather-page">
      {weatherPopup && (
        <div className="weather-signage-overlay" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setWeatherPopup(null);
        }}>
          <section className={`weather-signage-popup ${weatherPopup.severity}`} role="alertdialog" aria-modal="true" aria-labelledby="weather-signage-title">
            <button className="weather-signage-close" type="button" aria-label="Close weather alert" onClick={() => setWeatherPopup(null)}>×</button>
            <span className="eyebrow">HIGHWAY WEATHER ALERT</span>
            <h3 id="weather-signage-title">{weatherPopup.severity === "high" ? "Heavy rain warning" : "Adverse weather advisory"}</h3>
            <p><strong>{weatherPopup.route}</strong></p>
            <p>{weatherPopup.reason}</p>
            <div className="weather-signage-status">
              <strong>Roadside display status: Not sent</strong>
              <span>This project has no connected highway sign controller. This is an alert preview only.</span>
            </div>
            <button className="route-check-button" type="button" onClick={() => setWeatherPopup(null)}>GOT IT</button>
          </section>
        </div>
      )}
      <header className="weather-heading">
        <div>
          <span className="eyebrow">TRIP WEATHER INTELLIGENCE</span>
          <h2>Route Weather & Rain Alerts</h2>
          <p>Check forecast conditions along your planned drive, not just at one city.</p>
        </div>
        <span className="weather-provider-badge">Open-Meteo forecast</span>
      </header>

      <form className="route-search-panel" onSubmit={loadRoute}>
        <label>
          <span>FROM</span>
          <input value={origin} onChange={(event) => setOrigin(event.target.value)} required />
        </label>
        <span className="route-direction" aria-hidden="true">→</span>
        <label>
          <span>TO</span>
          <input value={destination} onChange={(event) => setDestination(event.target.value)} required />
        </label>
        <label className="departure-field">
          <span>DEPARTURE TIME</span>
          <input
            type="datetime-local"
            value={departure}
            min={INITIAL_DEPARTURE}
            onChange={(event) => setDeparture(event.target.value)}
            required
          />
        </label>
        <button className="route-check-button" type="submit" disabled={loading}>
          {loading ? "CHECKING ROUTE…" : "CHECK ROUTE WEATHER"}
        </button>
      </form>

      {error && <div className="route-weather-error">{error}</div>}
      {loading && <div className="route-weather-loading">Getting the driving route and weather forecast…</div>}

      {route && !loading && (
        <>
          <section className={`route-alert-banner ${route.weather_risk}`} role="status">
            <span className="route-alert-symbol">{route.heavy_rain_alert ? "⚠" : route.weather_risk === "moderate" ? "☂" : "✓"}</span>
            <div>
              <strong>
                {route.heavy_rain_alert
                  ? "Heavy rain forecast along your route"
                  : route.weather_risk === "moderate"
                    ? "Rain may affect parts of your route"
                    : "No significant rain forecast along this route"}
              </strong>
              <p>
                {route.heavy_rain_alert
                  ? highRiskPoints.map((point) => `Around ${point.distance_km} km (${formatTime(point.arrival_time)})`).join(" · ")
                  : route.weather_risk === "moderate"
                    ? `${moderateRiskPoints.length} route point${moderateRiskPoints.length === 1 ? "" : "s"} show rain or elevated rain probability.`
                    : "Forecast checked at multiple points using your departure time."}
              </p>
            </div>
            <span className="route-risk-pill">{route.weather_risk} risk</span>
          </section>

          {route.heavy_rain_alert && (
            <section className="alternate-route-advisory" role="status">
              <span className="alternate-route-icon" aria-hidden="true">↗</span>
              <div className="alternate-route-copy">
                <span className="eyebrow">HEAVY RAIN ROUTE ADVISORY</span>
                {route.alternate_route ? (
                  <>
                    <h3>Lower-rain alternative available</h3>
                    <p>
                      The dashed green line on the map avoids some forecast rain checkpoints. Weather is still advisory; check local road conditions before travelling.
                    </p>
                    <div className="alternate-route-metrics">
                      <span><strong>{route.alternate_route.distance_km} km</strong> distance</span>
                      <span><strong>{route.alternate_route.duration_minutes} min</strong> estimated drive</span>
                      <span className={`route-risk-pill ${route.alternate_route.weather_risk}`}>
                        {route.alternate_route.weather_risk} rain risk
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <h3>No lower-rain alternative found</h3>
                    <p>
                      The routing service did not return an alternate route with fewer forecast rain-risk points. Consider delaying travel if conditions are severe.
                    </p>
                  </>
                )}
              </div>
            </section>
          )}

          <section className="route-overview-grid">
            <article className="route-overview-card">
              <span>DRIVING DISTANCE</span>
              <strong>{route.distance_km} <small>km</small></strong>
            </article>
            <article className="route-overview-card">
              <span>ESTIMATED DRIVE</span>
              <strong>{route.duration_minutes} <small>min</small></strong>
            </article>
            <article className="route-overview-card">
              <span>WEATHER CHECKPOINTS</span>
              <strong>{route.points.length}</strong>
            </article>
            <article className="route-overview-card">
              <span>DEPARTURE</span>
              <strong>{formatTime(route.departure_time)}</strong>
            </article>
          </section>

          <section className="route-weather-panel road-conditions-panel">
            <div className="route-section-heading">
              <div>
                <span className="eyebrow">ESTIMATED FROM FORECAST</span>
                <h3>Road conditions along route</h3>
              </div>
              <span className={`road-condition-summary ${route.road_condition_risk || route.weather_risk}`}>
                {route.road_condition_summary || "Forecast available"}
              </span>
            </div>
            <div className="road-condition-list">
              {route.points.map((point) => (
                <article className={`road-condition-item ${point.road_condition_risk || point.risk}`} key={`road-${point.index}`}>
                  <div>
                    <span>ABOUT {point.distance_km} KM · {formatTime(point.arrival_time)}</span>
                    <strong>{point.road_condition || (point.heavy_rain ? "High water risk" : point.risk === "moderate" ? "Wet / slippery risk" : "Likely dry")}</strong>
                  </div>
                  <p>{point.road_advice || point.alert}</p>
                  <small>Rain {point.precipitation_mm} mm · Visibility {point.visibility_m == null ? "—" : point.visibility_m >= 1000 ? `${(point.visibility_m / 1000).toFixed(1)} km` : `${point.visibility_m} m`}</small>
                </article>
              ))}
            </div>
            <p className="road-condition-note">Forecast-based estimates only. This does not confirm live flooding, potholes, closures, or pavement state.</p>
          </section>

          <section className="route-weather-panel">
            <div className="route-section-heading">
              <div>
                <span className="eyebrow">DRIVING ROUTE</span>
                <h3>{route.origin.name} → {route.destination.name}</h3>
              </div>
              <span className="route-source-label">Road route via OpenStreetMap</span>
            </div>
            <RouteMap
              route={route}
              positions={positions}
              alternatePositions={alternatePositions}
              allRoutePositions={allRoutePositions}
            />
          </section>

          <section className="route-weather-panel route-checkpoints-panel">
            <div className="route-section-heading">
              <div>
                <span className="eyebrow">FORECAST AT ESTIMATED ARRIVAL</span>
                <h3>Weather along the route</h3>
              </div>
              <span className="route-source-label">Times are local to India</span>
            </div>
            <div className="route-checkpoint-list">
              {route.points.map((point) => (
                <article className={`route-checkpoint ${point.risk}`} key={point.index}>
                  <div className="checkpoint-distance">
                    <span>POINT {String(point.index).padStart(2, "0")}</span>
                    <strong>{point.distance_km} <small>km</small></strong>
                  </div>
                  <div className="checkpoint-arrival">
                    <span>EST. ARRIVAL</span>
                    <strong>{formatTime(point.arrival_time)}</strong>
                  </div>
                  <div className="checkpoint-rain">
                    <span>RAINFALL / CHANCE</span>
                    <strong>{point.precipitation_mm} mm <small>· {point.precipitation_probability}%</small></strong>
                  </div>
                  <div className="checkpoint-wind">
                    <span>WIND</span>
                    <strong>{point.wind_speed_kmh} <small>km/h</small></strong>
                  </div>
                  <span className={`checkpoint-risk ${point.risk}`}>{point.risk === "high" ? "HEAVY RAIN" : point.risk === "moderate" ? "RAIN WATCH" : "LOW RISK"}</span>
                </article>
              ))}
            </div>
          </section>

          <p className="route-weather-disclaimer">{route.note} Source: {route.source}.</p>
        </>
      )}
    </div>
  );
}
