import React, { useCallback, useEffect, useState } from "react";
import { getActiveRouteWeatherAlert } from "../utils/routeWeatherAlerts";

export default function Alerts() {
  const [routeWeather, setRouteWeather] = useState(getActiveRouteWeatherAlert);
  const [accidentAlerts, setAccidentAlerts] = useState([]);
  const [floodAlerts, setFloodAlerts] = useState([]);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  const [alertActionError, setAlertActionError] = useState("");

  useEffect(() => {
    const refreshRouteAlert = () => setRouteWeather(getActiveRouteWeatherAlert());
    window.addEventListener("storage", refreshRouteAlert);
    window.addEventListener("focus", refreshRouteAlert);
    return () => {
      window.removeEventListener("storage", refreshRouteAlert);
      window.removeEventListener("focus", refreshRouteAlert);
    };
  }, []);

  const loadAccidentAlerts = useCallback(async () => {
    setLoadingAlerts(true);
    setAlertActionError("");
    try {
      const response = await fetch("http://127.0.0.1:8000/api/reports");
      if (!response.ok) throw new Error("Could not refresh alerts.");
      const reports = await response.json();
      if (!Array.isArray(reports)) return;

      const events = reports.flatMap((report) =>
        (report.results?.accident_events || []).map((event) => {
          const seconds = Math.max(0, Number(event.time_seconds) || 0);
          const minute = Math.floor(seconds / 60);
          const second = Math.floor(seconds % 60).toString().padStart(2, "0");
          return {
            id: `${report.id}-accident-${event.event}`,
            type: "ACCIDENT DETECTED",
            severity: "HIGH",
            title: `Possible accident in ${report.name || "video analysis"}`,
            description: `Video time ${minute}:${second} · AI confidence ${Math.round((event.confidence || 0) * 100)}% · frame ${event.frame ?? "—"}.`,
            time: report.created_at
              ? `Analyzed ${new Date(report.created_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}`
              : "From saved video analysis",
            icon: "🚑",
            evidenceUrl: event.evidence_url
              ? `http://127.0.0.1:8000${event.evidence_url}`
              : "",
            videoUrl: report.results?.video_url
              ? `http://127.0.0.1:8000${report.results.video_url}#t=${Math.floor(seconds)}`
              : "",
          };
        })
      );
      const roadEvents = reports.flatMap((report) => {
        const road = report.results?.road_condition;
        // Older reports could label bright lane paint as flooding from a
        // single reflection cue. Require the repeated wet-surface evidence
        // produced by the current backend before showing a flood alert.
        if (
          !road?.possible_flooding
          || Number(road.flood_sample_count || 0) < 2
          || Number(road.flood_sample_ratio || 0) < 0.35
          || Number(road.wet_surface_frame_ratio || 0) < 0.35
        ) return [];
        const seconds = Math.max(0, Number(road.flood_time_seconds) || 0);
        const minute = Math.floor(seconds / 60);
        const second = Math.floor(seconds % 60).toString().padStart(2, "0");
        return [{
          id: `${report.id}-possible-flooding`,
          type: "ROAD FLOOD RISK",
          severity: "HIGH",
          title: `Possible flooded road in ${report.name || "video analysis"}`,
          description: `Repeated wet-surface and broad reflection cues appeared in ${road.flood_sample_count ?? 0} sampled frames. Video time ${minute}:${second}. Treat as a possible hazard; water depth and safe passability are not verified.`,
          time: report.created_at
            ? `Analyzed ${new Date(report.created_at).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}`
            : "From saved video analysis",
          icon: "🌊",
          evidenceUrl: road.evidence_url
            ? `http://127.0.0.1:8000${road.evidence_url}`
            : "",
          videoUrl: report.results?.video_url
            ? `http://127.0.0.1:8000${report.results.video_url}#t=${Math.floor(seconds)}`
            : "",
        }];
      });
      setAccidentAlerts(events);
      setFloodAlerts(roadEvents);
    } catch (error) {
      setAlertActionError(error.message || "Could not refresh alerts.");
    } finally {
      setLoadingAlerts(false);
    }
  }, []);

  useEffect(() => {
    loadAccidentAlerts();
    window.addEventListener("focus", loadAccidentAlerts);
    return () => window.removeEventListener("focus", loadAccidentAlerts);
  }, [loadAccidentAlerts]);

  const clearAccidentEvidence = async () => {
    const confirmed = window.confirm(
      "Delete all saved accident evidence images and remove accident events from saved reports? This cannot be undone."
    );
    if (!confirmed) return;

    setLoadingAlerts(true);
    setAlertActionError("");
    try {
      const response = await fetch("http://127.0.0.1:8000/api/accident-evidence", {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not clear accident evidence.");
      setAccidentAlerts([]);
      await loadAccidentAlerts();
    } catch (error) {
      setAlertActionError(error.message || "Could not clear accident evidence.");
      setLoadingAlerts(false);
    }
  };

  const warningPoints = (routeWeather?.points || [])
    .filter((point) => point.heavy_rain || point.risk === "moderate");
  const peakPoint = [...warningPoints].sort(
    (a, b) => (b.precipitation_mm || 0) - (a.precipitation_mm || 0)
  )[0];
  const severity = routeWeather?.heavy_rain_alert ? "HIGH" : "MEDIUM";
  const routeAlert = routeWeather
    ? {
        id: `weather-${routeWeather.departure_time}`,
        type: "ROUTE WEATHER",
        severity,
        title: routeWeather.heavy_rain_alert
          ? "Heavy rain forecast on planned route"
          : "Rain risk on planned route",
        description: peakPoint
          ? `${routeWeather.origin.name} → ${routeWeather.destination.name}: rain risk around ${peakPoint.distance_km} km from origin near ${new Date(peakPoint.arrival_time).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} (${peakPoint.precipitation_mm} mm, ${peakPoint.precipitation_probability}% chance).`
          : `${routeWeather.origin.name} → ${routeWeather.destination.name}: ${routeWeather.weather_risk} weather risk is forecast along the trip.`,
        time: `Trip starts ${new Date(routeWeather.departure_time).toLocaleString([], { dateStyle: "short", timeStyle: "short" })}`,
        icon: "🌧️",
      }
    : null;
  const alerts = [...accidentAlerts, ...floodAlerts, ...(routeAlert ? [routeAlert] : [])];
  const highPriorityCount = alerts.filter((alert) => alert.severity === "HIGH").length;
  const mediumPriorityCount = alerts.filter((alert) => alert.severity === "MEDIUM").length;
  const refreshAlerts = () => {
    setRouteWeather(getActiveRouteWeatherAlert());
    loadAccidentAlerts();
  };

  return (
    <div className="page alerts-page">

      <div className="page-heading">
        <div>
          <span className="eyebrow">TRAFFIC &amp; ROUTE ALERT CENTER</span>

          <h2>Traffic Alerts</h2>

          <p>
            Review accident and possible flood warnings from analyzed videos, plus weather alerts for your saved route.
          </p>
        </div>

        <div className="dashboard-status">
          <span className="status-dot"></span>
          ALERT ENGINE READY
        </div>
      </div>

      <div className="alert-summary">

        <div className="alert-summary-card">
          <span className="summary-icon danger">🚨</span>

          <div>
            <small>HIGH PRIORITY</small>
            <strong>{highPriorityCount}</strong>
          </div>
        </div>

        <div className="alert-summary-card">
          <span className="summary-icon warning">⚠</span>

          <div>
            <small>MEDIUM PRIORITY</small>
            <strong>{mediumPriorityCount}</strong>
          </div>
        </div>

        <div className="alert-summary-card">
          <span className="summary-icon normal">✓</span>

          <div>
            <small>SYSTEM STATUS</small>
            <strong>{routeWeather ? "ROUTE WATCH" : accidentAlerts.length || floodAlerts.length ? "VIDEO ALERTS" : "NO ACTIVE ROUTE"}</strong>
          </div>
        </div>

      </div>

      <section className="dashboard-panel alerts-panel">

        <div className="panel-header">

          <div>
            <span className="eyebrow">
              TRAFFIC, SAFETY &amp; ROUTE ADVISORIES
            </span>

            <h3>Recent Alerts</h3>
          </div>

          <div className="alerts-header-actions">
            <button
              type="button"
              className="alerts-refresh-button"
              onClick={refreshAlerts}
              disabled={loadingAlerts}
              title="Refresh alerts and saved evidence"
            >
              <span aria-hidden="true">↻</span>
              {loadingAlerts ? "REFRESHING" : "REFRESH"}
            </button>
            {accidentAlerts.length > 0 && (
              <button
                type="button"
                className="alerts-clear-button"
                onClick={clearAccidentEvidence}
                disabled={loadingAlerts}
              >
                CLEAR EVIDENCE
              </button>
            )}
            <span className="ai-badge">
              {accidentAlerts.length + floodAlerts.length
                ? `${accidentAlerts.length + floodAlerts.length} VIDEO ALERT${accidentAlerts.length + floodAlerts.length === 1 ? "" : "S"}`
                : routeAlert
                ? "ROUTE WEATHER"
                : "NO ACTIVE ALERTS"}
            </span>
          </div>

        </div>

        {alertActionError && (
          <p className="alerts-action-error" role="alert">{alertActionError}</p>
        )}

        <div className="alerts-list">

          {alerts.map((alert) => (
            <div
              className={`alert-row ${alert.severity.toLowerCase()}`}
              key={alert.id}
            >

              <div className="alert-icon">
                {alert.icon}
              </div>

              <div className="alert-content">

                <div className="alert-top">

                  <span className="alert-type">
                    {alert.type}
                  </span>

                  <span
                    className={`severity-badge ${alert.severity.toLowerCase()}`}
                  >
                    {alert.severity}
                  </span>

                </div>

                <strong>
                  {alert.title}
                </strong>

                <p>
                  {alert.description}
                </p>

                {alert.evidenceUrl && (
                  <a
                    className="alert-evidence-link"
                    href={alert.evidenceUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <img
                      className="alert-evidence-image"
                      src={alert.evidenceUrl}
                      alt={`Visual evidence for ${alert.title}`}
                    />
                    <span>OPEN EVIDENCE ↗</span>
                  </a>
                )}

                {alert.videoUrl && (
                  <a
                    className="alert-video-link"
                    href={alert.videoUrl}
                    target="_blank"
                    rel="noreferrer"
                  >
                    OPEN VIDEO AT EVENT ↗
                  </a>
                )}

              </div>

              <div className="alert-time">
                {alert.time}
              </div>

            </div>
          ))}

          {!alerts.length && (
            <div className="alerts-empty">
              <span aria-hidden="true">☀️</span>
              <div>
                <strong>No traffic or weather alerts</strong>
                <p>Accident events from video analysis and route-weather warnings will appear here.</p>
              </div>
              <a href="/weather">CHECK A ROUTE →</a>
            </div>
          )}

        </div>

      </section>

      <div className="alerts-bottom">

        <section className="dashboard-panel">

          <div className="panel-header">

            <div>
              <span className="eyebrow">
                ALERT RULES
              </span>

              <h3>Detection Rules</h3>
            </div>

          </div>

          <div className="rule-list">

            <div className="rule-row">
              <div>
                <strong>Possible Accident</strong>
                <span>
                  Confirmed detections include a saved evidence frame and video timestamp
                </span>
              </div>

              <b className="rule-active">
                ACTIVE
              </b>
            </div>

            <div className="rule-row">
              <div>
                <strong>Possible Flooded Road</strong>
                <span>Flag repeated broad water-like cues in sampled video frames</span>
              </div>
              <b className="rule-active">ACTIVE</b>
            </div>

            <div className="rule-row">
              <div>
                <strong>Speed Violation</strong>
                <span>
                  Vehicle exceeds configured speed limit
                </span>
              </div>

              <b className="rule-active">
                ACTIVE
              </b>
            </div>

            <div className="rule-row">
              <div>
                <strong>High Congestion</strong>
                <span>
                  Excessive active vehicles detected
                </span>
              </div>

              <b className="rule-active">
                ACTIVE
              </b>
            </div>

            <div className="rule-row">
              <div>
                <strong>Vehicle Flow</strong>
                <span>
                  Monitor traffic movement across count line
                </span>
              </div>

              <b className="rule-active">
                ACTIVE
              </b>
            </div>

            <div className="rule-row">
              <div>
                <strong>Route Weather Warning</strong>
                <span>
                  Flag rain and heavy-rain forecasts along a planned trip
                </span>
              </div>

              <b className="rule-active">
                ACTIVE
              </b>
            </div>

          </div>

        </section>

        <section className="dashboard-panel">

          <div className="panel-header">

            <div>
              <span className="eyebrow">
                AI PIPELINE
              </span>

              <h3>Alert Sources</h3>
            </div>

          </div>

          <div className="alert-source-list">

            <div>
              <span className="source-icon">👁</span>

              <div>
                <strong>YOLO Detection</strong>
                <small>
                  Vehicle classification
                </small>
              </div>

              <b>READY</b>
            </div>

            <div>
              <span className="source-icon">🎯</span>

              <div>
                <strong>ByteTrack</strong>
                <small>
                  Persistent object tracking
                </small>
              </div>

              <b>READY</b>
            </div>

            <div>
              <span className="source-icon">📊</span>

              <div>
                <strong>Analytics Engine</strong>
                <small>
                  Traffic measurements
                </small>
              </div>

              <b>READY</b>
            </div>

            <div>
              <span className="source-icon">🚑</span>

              <div>
                <strong>Accident Detection</strong>
                <small>
                  Confirmed video events with saved evidence frames
                </small>
              </div>

              <b>READY</b>
            </div>

            <div>
              <span className="source-icon">🌧️</span>

              <div>
                <strong>Route Weather Forecast</strong>
                <small>
                  Rain alerts at estimated trip arrival times
                </small>
              </div>

              <b>READY</b>
            </div>

            <div>
              <span className="source-icon">🌊</span>
              <div>
                <strong>Road Flood Cue Check</strong>
                <small>Visual water-like surface estimate from analyzed video</small>
              </div>
              <b>READY</b>
            </div>

          </div>

        </section>

      </div>

    </div>
  );
}
