import React, { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    fetch(`${API}/api/reports`, { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load reports");
        return data;
      })
      .then((data) => {
        if (!active) return;
        setReports(data);
        setSelectedId((current) => current || data[0]?.id || null);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const selected = reports.find((report) => report.id === selectedId);
  const results = selected?.results || {};
  const vehicles = results.vehicles || {};
  const helmetRecords = results.helmet_records || [];
  const plateRecords = Array.isArray(results.vehicle_plates)
    ? results.vehicle_plates.filter((record) => record.number_plate)
    : [];

  const refreshReports = async () => {
    setRefreshing(true);
    setError("");
    try {
      const response = await fetch(`${API}/api/reports/refresh`, {
        method: "POST",
        cache: "no-store",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load reports");
      setReports(data);
      setSelectedId((current) =>
        data.some((report) => report.id === current)
          ? current
          : data[0]?.id ?? null
      );
    } catch (err) {
      setError(err.message || "Could not refresh reports");
    } finally {
      setRefreshing(false);
    }
  };

  const deleteReport = async (report) => {
    const confirmed = window.confirm(
      `Delete “${report.name}” and its uploaded/processed videos and evidence? This cannot be undone.`
    );
    if (!confirmed) return;

    setDeletingId(report.id);
    setError("");
    try {
      const response = await fetch(`${API}/api/reports/${encodeURIComponent(report.id)}`, {
        method: "DELETE",
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not delete report");

      const remainingReports = reports.filter((item) => item.id !== report.id);
      setReports(remainingReports);
      if (selectedId === report.id) {
        setSelectedId(remainingReports[0]?.id ?? null);
      }
    } catch (err) {
      setError(err.message || "Could not delete report");
    } finally {
      setDeletingId(null);
    }
  };

  const exportSelected = () => {
    if (!selected) return;
    const blob = new Blob([JSON.stringify(selected, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${selected.name.replace(/[^a-z0-9-_]+/gi, "_")}_report.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page reports-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">TRAFFIC REPORTING</span>
          <h2>Reports & Evidence</h2>
          <p>Completed uploaded video analyses are saved here with their AI results.</p>
        </div>
        <div className="dashboard-status">
          <span className="status-dot"></span>
          {loading ? "LOADING REPORTS" : "REPORTS SAVED"}
        </div>
      </div>

      <div className="report-summary">
        <div><span>REPORTS</span><strong>{reports.length}</strong><small>Completed analyses</small></div>
        <div><span>DATA SOURCE</span><strong>AI</strong><small>YOLO + ByteTrack</small></div>
        <div><span>OUTPUT</span><strong>VIDEO</strong><small>Annotated evidence</small></div>
        <div><span>STATUS</span><strong>{loading ? "…" : error ? "ERROR" : "READY"}</strong><small>{error || (reports.length ? "Latest analysis saved" : "Waiting for analysis")}</small></div>
      </div>

      <section className="dashboard-panel reports-panel">
        <div className="panel-header">
          <div><span className="eyebrow">GENERATED REPORTS</span><h3>Analysis Reports</h3></div>
          <div className="alerts-header-actions">
            <button
              type="button"
              className="alerts-refresh-button"
              onClick={refreshReports}
              disabled={refreshing}
              title="Refresh saved reports"
            >
              <span aria-hidden="true">↻</span>
              {refreshing ? "REFRESHING" : "REFRESH"}
            </button>
            <span className="ai-badge">AI GENERATED</span>
          </div>
        </div>

        <div className="reports-table">
          <div className="report-table-header">
            <span>REPORT</span><span>TYPE</span><span>DATE</span><span>STATUS</span><span>ACTION</span>
          </div>
          {reports.map((report) => (
            <div className="report-table-row" key={report.id}>
              <div className="report-name">
                <div className="report-icon">▤</div>
                <div><strong>{report.name}</strong><small>{report.id}</small></div>
              </div>
              <span className="report-type">{report.type}</span>
              <span className="report-date">{formatDate(report.created_at)}</span>
              <span className="report-ready">● {report.status}</span>
              <div className="report-row-actions">
                <button className="report-action" onClick={() => setSelectedId(report.id)}>
                  {selectedId === report.id ? "VIEWING" : "VIEW →"}
                </button>
                <button
                  className="report-delete-action"
                  onClick={() => deleteReport(report)}
                  disabled={deletingId === report.id}
                  title={`Delete ${report.name}`}
                >
                  {deletingId === report.id ? "DELETING" : "DELETE"}
                </button>
              </div>
            </div>
          ))}
          {!loading && reports.length === 0 && (
            <div className="no-plates-message">
              <span>📄</span>
              <div><strong>No saved reports yet</strong><p>Upload and complete a video analysis to create a report.</p></div>
            </div>
          )}
        </div>
      </section>

      {selected && (
        <section className="dashboard-panel reports-panel">
          <div className="panel-header">
            <div><span className="eyebrow">SAVED ANALYSIS</span><h3>{selected.name}</h3></div>
            <button className="secondary-action" onClick={exportSelected}>EXPORT JSON ↓</button>
          </div>
          <div className="report-content-grid">
            <div><span>🚗</span><strong>{results.unique_vehicles ?? 0} Vehicles</strong><small>Unique tracked vehicles</small></div>
            <div><span>🚘</span><strong>{vehicles.car ?? 0} Cars</strong><small>Vehicle classification</small></div>
            <div><span>🏍️</span><strong>{vehicles.motorcycle ?? 0} Motorcycles</strong><small>{results.total_helmet_checked ?? 0} checked for helmets</small></div>
            <div><span>🚌</span><strong>{vehicles.bus ?? 0} Buses</strong><small>Vehicle classification</small></div>
            <div><span>🚚</span><strong>{vehicles.truck ?? 0} Trucks</strong><small>Vehicle classification</small></div>
            <div><span>🚐</span><strong>{vehicles.van ?? 0} Vans</strong><small>YOLO-World open-vocabulary detections</small></div>
            <div><span>🚛</span><strong>{vehicles.heavy_vehicle ?? 0} Unclear heavy vehicles</strong><small>Conflicting bus/truck evidence</small></div>
            <div><span>⚠️</span><strong>{vehicles.uncertain_vehicle ?? 0} Uncertain vehicle types</strong><small>Conflicting model classifications</small></div>
            <div><span>🛺</span><strong>{vehicles.auto_rickshaw ?? 0} Auto-rickshaws</strong><small>Estimated from vehicle shape</small></div>
            <div><span>🚕</span><strong>{vehicles.taxi ?? 0} Yellow taxis</strong><small>Estimated from shape and color</small></div>
            <div><span>🚑</span><strong>{results.vehicle_detection_capabilities?.ambulance?.available ? `${vehicles.ambulance ?? 0} Ambulances` : "Ambulance model needed"}</strong><small>{results.vehicle_detection_capabilities?.ambulance?.available ? results.vehicle_detection_capabilities.ambulance.zero_shot ? "YOLOv8s-World zero-shot estimate" : "Trained ambulance detector" : results.vehicle_detection_capabilities?.ambulance?.reason || "Install ambulance detector"}</small></div>
            <div><span>🪖</span><strong>{results.helmet_wearing ?? 0} Helmet OK</strong><small>{results.helmet_not_wearing ?? 0} no helmet</small></div>
            <div><span>⚡</span><strong>{results.speed_violations ?? 0} Speed Violations</strong><small>Average speed {results.average_speed_kmh ?? 0} km/h</small></div>
            <div><span>🚦</span><strong>{results.congestion || "Unknown"}</strong><small>Traffic congestion</small></div>
            <div><span>↕️</span><strong>{results.line_crossings ?? results.vehicles_crossed ?? 0} Crossings</strong><small>Line crossings detected</small></div>
            <div><span>⚠️</span><strong>{results.total_accidents ?? 0} Accidents</strong><small>Accident events detected</small></div>
            <div><span>🔎</span><strong>{results.total_plates_detected ?? 0} Plate numbers</strong><small>Recognized by OCR</small></div>
          </div>
          {results.video_url && (
            <p><a className="secondary-action" href={`${API}${results.video_url}`} target="_blank" rel="noreferrer">OPEN PROCESSED VIDEO ↗</a></p>
          )}
          {plateRecords.length > 0 && (
            <div className="report-helmet-list">
              <h4>Number plate reads</h4>
              {plateRecords.map((record) => {
                const isReliable = record.reads > 1
                  && record.agreement >= 0.67
                  && record.confidence >= 0.35
                  && record.ocr_confidence >= 0.5;
                return (
                  <div className="report-helmet-row" key={`plate-${record.vehicle_id}`}>
                    <span>{String(record.vehicle || "vehicle").replace(/_/g, " ")} #{record.vehicle_id}</span>
                    <strong>{record.number_plate}</strong>
                    <small>{isReliable ? "Repeated read · high confidence" : `LOW CONFIDENCE · detector ${Math.round((record.confidence || 0) * 100)}% · OCR ${Math.round((record.ocr_confidence || 0) * 100)}%`}</small>
                  </div>
                );
              })}
            </div>
          )}
          {helmetRecords.length > 0 && (
            <div className="report-helmet-list">
              <h4>Helmet detections</h4>
              {helmetRecords.map((record) => {
                const helmetStatus = record.helmet_status || "uncertain";
                const plate = record.number_plate || record.plate || "";
                return (
                  <div className="report-helmet-row" key={record.vehicle_id}>
                    {record.crop_url ? (
                      <img
                        className="report-helmet-image"
                        src={`${API}${record.crop_url}`}
                        alt={`Rider and motorcycle for Bike #${record.vehicle_id}`}
                      />
                    ) : null}
                    <span>Bike #{record.vehicle_id}</span>
                    <strong>
                      {helmetStatus === "without_helmet"
                        ? "NO HELMET"
                        : helmetStatus === "with_helmet"
                        ? "HELMET OK"
                        : "UNCERTAIN"}
                    </strong>
                    <small>
                      {record.confidence
                        ? `${Math.round(record.confidence * 100)}% confidence`
                        : "Confidence unavailable"}
                      {plate ? ` · Plate: ${plate}` : ""}
                    </small>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
