import React, { useEffect, useState } from "react";

const API = "http://127.0.0.1:8000";
const ANALYSIS_STORAGE_KEY = "smartTrafficAI.analysisJob";

function ResultCard({ title, value, subtitle, icon }) {
  return (
    <div className="analysis-result-card">
      <span className="analysis-result-icon">{icon}</span>
      <small>{title}</small>
      <strong>{value}</strong>
      <span>{subtitle}</span>
    </div>
  );
}

function PlateTable({ records }) {
  const entries = Array.isArray(records)
    ? records.filter((record) => record.number_plate)
    : [];
  const uniquePlateCount = new Set(entries.map((record) => record.number_plate)).size;

  return (
    <section className="detected-plates-panel">

      <div className="detected-plates-header">

        <div>
          <span className="eyebrow">
            ANPR RESULTS
          </span>

          <h3>
            Detected Vehicles & Number Plates
          </h3>

          <p>
            Vehicles detected in the video with their
            corresponding number plate numbers.
          </p>
        </div>

        <div className="plates-count">
          <strong>{uniquePlateCount}</strong>
          <span>PLATE READS</span>
        </div>

      </div>

      {entries.length > 0 ? (

        <div className="plates-table-wrapper">

          <table className="plates-table">

            <thead>
              <tr>
                <th>#</th>
                <th>VEHICLE ID</th>
                <th>NUMBER PLATE</th>
                <th>STATUS</th>
              </tr>
            </thead>

            <tbody>

              {entries.map(
                (record, index) => (

                  <tr key={`${record.vehicle_id}-${record.number_plate}-${index}`}>

                    <td>
                      {index + 1}
                    </td>

                    <td>
                      <div className="vehicle-id-cell">
                        <span className="vehicle-icon">
                          🚗
                        </span>

                        <strong>
                          {record.vehicle_id == null
                            ? "Vehicle association unavailable"
                            : `${String(record.vehicle || "vehicle").replace(/_/g, " ").replace(/^./, (char) => char.toUpperCase())} #${record.vehicle_id}`}
                        </strong>
                      </div>
                    </td>

                    <td>
                        <span className="plate-number">
                          {record.number_plate}
                      </span>
                    </td>

                    <td>
                        <span className={`plate-status ${record.plate_status === "readable" && record.reads > 1 && record.agreement >= 0.67 && record.confidence >= 0.35 && record.ocr_confidence >= 0.5 ? "" : "plate-status-review"}`}>
                          {record.reads > 1 && record.agreement >= 0.67 && record.confidence >= 0.35 && record.ocr_confidence >= 0.5
                              ? `Repeated read · ${record.reads} frames`
                              : `LOW CONFIDENCE · OCR ${Math.round((record.ocr_confidence || 0) * 100)}%`}
                      </span>
                    </td>

                  </tr>

                )
              )}

            </tbody>

          </table>

        </div>

      ) : (

        <div className="no-plates-message">
          <span>🔍</span>

          <div>
            <strong>
              No plate numbers were read
            </strong>

            <p>
              Detected plate regions are listed here when OCR returns a plate number.
            </p>
          </div>
        </div>

      )}

    </section>
  );
}

function HelmetTable({ results }) {
  const records = Array.isArray(results?.helmet_records)
    ? results.helmet_records
    : [];

  const wearing =
    results?.helmet_wearing ??
    results?.helmet_wearing_count ??
    records.filter((r) => r.helmet_status === "with_helmet").length;

  const notWearing =
    results?.helmet_not_wearing ??
    results?.helmet_violations ??
    records.filter((r) => r.helmet_status === "without_helmet").length;

  const checked =
    results?.total_helmet_checked ??
    results?.helmet_checked ??
    records.length;

  return (
    <section className="helmet-analysis-panel">
      <div className="helmet-analysis-header">
        <div>
          <span className="eyebrow">HELMET DETECTION</span>
          <h3>Motorcycle Helmet Analysis</h3>
          <p>
            Review images show the rider and motorcycle, with the helmet model's detected region marked.
            Uncertain results are not counted as violations.
          </p>
        </div>

        <div className="helmet-model-badge">
          🪖 Helmet Detection AI
        </div>
      </div>

      <div className="helmet-summary-grid">
        <ResultCard
          title="MOTORCYCLES CHECKED"
          value={checked}
          subtitle="Rider regions analyzed"
          icon="🏍️"
        />
        <ResultCard
          title="HELMET WEARING"
          value={wearing}
          subtitle="Confirmed helmet"
          icon="🪖"
        />
        <ResultCard
          title="NO HELMET"
          value={notWearing}
          subtitle="Confirmed violations"
          icon="❌"
        />
      </div>

      {records.length > 0 ? (
        <div className="helmet-record-grid">
          {records.map((record, index) => {
            const status = record.helmet_status || record.status || "unknown";
            const confidence = Number(
              record.confidence ?? record.helmet_confidence ?? 0
            );
            const isViolation = status === "without_helmet";
            const isWearing = status === "with_helmet";
            const isUncertain = !isViolation && !isWearing;
            const plate = record.number_plate || record.plate || "";

            return (
              <article
                className={`helmet-record-card ${
                  isViolation
                    ? "helmet-record-danger"
                    : isWearing
                    ? "helmet-record-safe"
                    : "helmet-record-uncertain"
                }`}
                key={`${record.vehicle_id ?? record.track_id ?? index}-${index}`}
              >
                <div className="helmet-crop-box">
                  {record.crop_url ? (
                    <img
                      src={`${API}${record.crop_url}`}
                      alt={`Rider, motorcycle, and helmet detection for Bike #${
                        record.vehicle_id ?? record.track_id ?? index + 1
                      }`}
                    />
                  ) : (
                    <div className="helmet-no-image">
                      🏍️
                      <span>Rider crop unavailable</span>
                    </div>
                  )}

                  <span
                    className={`helmet-image-status ${
                      isViolation
                        ? "helmet-danger"
                        : isWearing
                        ? "helmet-safe"
                        : "helmet-uncertain"
                    }`}
                  >
                    {isViolation
                      ? "❌ NO HELMET"
                      : isWearing
                      ? "✓ HELMET OK"
                      : "⚠ UNCERTAIN"}
                  </span>
                </div>

                <div className="helmet-record-info">
                  <div className="helmet-record-title">
                    <strong>
                      🏍️ Bike #{record.vehicle_id ?? record.track_id ?? "—"}
                    </strong>
                    <span>
                      {confidence > 0
                        ? `${Math.round(confidence * 100)}%`
                        : "—"}
                    </span>
                  </div>

                  {plate && (
                    <div className="helmet-plate-row">
                      <span>NUMBER PLATE</span>
                      <strong>{plate}</strong>
                    </div>
                  )}

                  <div className="helmet-status-row">
                    <span>HELMET STATUS</span>
                    <strong>
                      {isViolation
                        ? "NO HELMET"
                        : isWearing
                        ? "HELMET OK"
                        : "UNCERTAIN"}
                    </strong>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="no-helmet-message">
          <span>🪖</span>
          <div>
            <strong>No confirmed helmet detections</strong>
            <p>
              The AI did not confidently classify any motorcycle rider
              in this video.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

export default function AIAnalysis() {

  const [file, setFile] = useState(null);

  const [job, setJob] = useState(() => {
    try {
      const saved = localStorage.getItem(ANALYSIS_STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [error, setError] = useState("");

  useEffect(() => {
    try {
      if (job) {
        localStorage.setItem(
          ANALYSIS_STORAGE_KEY,
          JSON.stringify(job)
        );
      } else {
        localStorage.removeItem(
          ANALYSIS_STORAGE_KEY
        );
      }
    } catch (storageError) {
      console.warn(
        "Unable to save analysis state:",
        storageError
      );
    }
  }, [job]);

  const refreshAnalysis = () => {
    const confirmed = window.confirm(
      "Refresh Analysis? This will clear the current analysis result."
    );

    if (!confirmed) return;

    localStorage.removeItem(
      ANALYSIS_STORAGE_KEY
    );

    setJob(null);
    setFile(null);
    setError("");

    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  };

  useEffect(() => {

    if (
      !job?.job_id ||
      ["completed", "failed"].includes(
        job.status
      )
    ) {
      return;
    }

    const interval = setInterval(
      async () => {

        try {

          const response = await fetch(
            `${API}/api/jobs/${job.job_id}`
          );

          if (response.status === 404) {
            localStorage.removeItem(ANALYSIS_STORAGE_KEY);
            setJob(null);
            setError(
              "This analysis job is no longer available. The backend may have restarted; please upload the video again."
            );
            return;
          }

          const data =
            await response.json();

          if (!response.ok) {
            throw new Error(
              data.detail ||
              "Unable to get job status"
            );
          }

          setJob((current) => {
            if (
              current?.job_id === data.job_id &&
              current?.status === data.status &&
              current?.progress === data.progress &&
              current?.message === data.message
            ) {
              return current;
            }
            return data;
          });

        } catch (err) {

          setError(
            err.message
          );

        }

      },
      1500
    );

    return () =>
      clearInterval(interval);

  }, [
    job?.job_id,
    job?.status
  ]);

  const uploadVideo = async () => {

    if (!file) return;

    setError("");

    setJob({
      status: "uploading",
      progress: 0,
      message:
        "Uploading traffic video..."
    });

    const formData =
      new FormData();

    formData.append(
      "file",
      file
    );

    try {

      const response =
        await fetch(
          `${API}/api/analyze`,
          {
            method: "POST",
            body: formData
          }
        );

      const data =
        await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail ||
          "Video upload failed"
        );

      }

      setJob(data);

    } catch (err) {

      setError(
        err.message
      );

      setJob(null);

    }
  };

  const results =
    job?.results;
  const accidentEvents = Array.isArray(results?.accident_events)
    ? results.accident_events
    : [];
  const roadCondition = results?.road_condition;
  const repeatedFloodEvidence = Boolean(
    roadCondition?.possible_flooding
    && Number(roadCondition.flood_sample_count || 0) >= 2
    && Number(roadCondition.flood_sample_ratio || 0) >= 0.35
    && Number(roadCondition.wet_surface_frame_ratio || 0) >= 0.35
  );
  const roadSurfaceLabel = roadCondition?.surface === "Possible flooding" && !repeatedFloodEvidence
    ? Number(roadCondition.wet_surface_frame_ratio || 0) >= 0.35
      ? "Possible wet surface"
      : "No sustained flood cues"
    : roadCondition?.surface || "Not assessable";
  const roadConditionNote = roadCondition?.surface === "Possible flooding" && !repeatedFloodEvidence
    ? "This saved result used the previous broad-reflection check, which can mistake road markings for water. Reanalyze the video to apply the updated repeated-cue check."
    : roadCondition?.note || "This is a visual estimate from sampled frames. It does not detect potholes or road damage.";
  const ambulanceCapability = results?.vehicle_detection_capabilities?.ambulance;
  const ambulanceAvailable = Boolean(ambulanceCapability?.available);
  const ambulanceResultIsLegacy = Boolean(
    ambulanceCapability
    && !ambulanceAvailable
    && /specialist-trained weights|required at/i.test(ambulanceCapability.reason || "")
  );

  return (

    <div className="page analysis-page">

      {/* =====================================================
          PAGE HEADER
      ===================================================== */}

      <div className="page-heading">

        <div>

          <span className="eyebrow">
            AI VISION ENGINE
          </span>

          <h2>
            Traffic Video Analysis
          </h2>

          <p>
            Upload a real traffic recording and let
            the AI detect, classify and track vehicles.
          </p>

        </div>

        <div className="analysis-header-actions">


          {job?.status === "completed" && (


            <button


              type="button"


              className="analysis-refresh-button"


              onClick={refreshAnalysis}


            >


              <span className="analysis-refresh-icon" aria-hidden="true">⟳</span>
              <span className="analysis-refresh-copy">
                <strong>NEW ANALYSIS</strong>
                <small>Clear current results</small>
              </span>


            </button>


          )}


          <div className="analysis-engine-status">


            <span className="status-dot"></span>


            YOLO + BYTETRACK READY


          </div>


        </div>

      </div>


      {/* =====================================================
          UPLOAD PANEL
      ===================================================== */}

      <section className="analysis-upload-panel">

        <div className="analysis-upload-content">

          <div className="upload-ai-icon">
            🎥
          </div>

          <span className="eyebrow">
            REAL VIDEO INPUT
          </span>

          <h3>
            Upload a traffic video
          </h3>

          <p>
            Use a road, highway, junction or CCTV
            recording. The AI will process the actual
            video frame by frame.
          </p>

          <label className="file-picker">

            <input
              type="file"
              accept="video/*"
              onChange={(event) => {

                setFile(
                  event.target.files?.[0] ||
                  null
                );

                setJob(null);

                setError("");

              }}
            />

            <span>

              {file
                ? "✓ " + file.name
                : "SELECT TRAFFIC VIDEO"}

            </span>

          </label>

          {file && (

            <div className="selected-file">

              <span>
                VIDEO SELECTED
              </span>

              <strong>
                {file.name}
              </strong>

            </div>

          )}

          <button
            className="primary-action analysis-button"
            onClick={uploadVideo}
            disabled={
              !file ||
              [
                "uploading",
                "processing"
              ].includes(
                job?.status
              )
            }
          >

            {job?.status ===
            "processing"

              ? `AI ANALYZING ${
                  job.progress || 0
                }%`

              : job?.status ===
                "uploading"

              ? "UPLOADING..."

              : "RUN REAL AI ANALYSIS →"}

          </button>

          {error && (

            <div className="analysis-error">
              ⚠ {error}
            </div>

          )}

          {job?.message && (

            <div className="analysis-status-message">
              {job.message}
            </div>

          )}

        </div>


        {/* =================================================
            CAPABILITIES
        ================================================= */}

        <div className="analysis-capabilities">

          <div>
            <span>01</span>
            <strong>
              Vehicle Detection
            </strong>
            <small>
              YOLO computer vision
            </small>
          </div>

          <div>
            <span>02</span>
            <strong>
              Object Tracking
            </strong>
            <small>
              ByteTrack vehicle IDs
            </small>
          </div>

          <div>
            <span>03</span>
            <strong>
              Number Plate Recognition
            </strong>
            <small>
              YOLO + EasyOCR
            </small>
          </div>

        </div>

      </section>


      {/* =====================================================
          PROCESSING
      ===================================================== */}

      {job?.status ===
        "processing" && (

        <section className="processing-panel">

          <div className="processing-header">

            <div>

              <span className="eyebrow">
                AI PROCESSING
              </span>

              <h3>
                Analyzing traffic video
              </h3>

            </div>

            <strong>
              {job.progress || 0}%
            </strong>

          </div>

          <div className="processing-bar">

            <div
              style={{
                width: `${
                  job.progress || 0
                }%`
              }}
            />

          </div>

          <p>
            YOLO is detecting vehicles, ByteTrack is
            assigning persistent tracking IDs and ANPR
            is reading number plates.
          </p>

        </section>

      )}


      {/* =====================================================
          RESULTS
      ===================================================== */}

      {results &&
        job?.status ===
          "completed" && (

        <section className="analysis-results">


          {/* =================================================
              RESULTS HEADER
          ================================================= */}

          <div className="results-heading">

            <div>

              <span className="eyebrow">
                ANALYSIS COMPLETE
              </span>

              <h3>
                Traffic intelligence generated
              </h3>

              <p>
                Results below are generated from the
                uploaded video by the AI processing pipeline.
              </p>

            </div>

            <div
              className={`congestion-badge ${String(
                results.congestion ||
                ""
              ).toLowerCase()}`}
            >
              {results.congestion ||
                "UNKNOWN"}{" "}
              CONGESTION
            </div>

          </div>


          {/* =================================================
              RESULT CARDS
          ================================================= */}

          <div className="analysis-results-grid">

            <ResultCard
              title="UNIQUE VEHICLES"
              value={
                results.unique_vehicles ??
                0
              }
              subtitle="Tracked IDs"
              icon="🚗"
            />

            <ResultCard
              title="CARS"
              value={
                results.vehicles?.car ??
                0
              }
              subtitle="Unique vehicles"
              icon="🚘"
            />

            <ResultCard
              title="MOTORCYCLES"
              value={
                results.vehicles
                  ?.motorcycle ??
                0
              }
              subtitle="Unique vehicles"
              icon="🏍️"
            />

            <ResultCard
              title="BUSES"
              value={
                results.vehicles?.bus ??
                0
              }
              subtitle="Unique vehicles"
              icon="🚌"
            />

            <ResultCard
              title="TRUCKS"
              value={
                results.vehicles?.truck ??
                0
              }
              subtitle="Unique vehicles"
              icon="🚚"
            />

            <ResultCard
              title="VANS"
              value={results.vehicles?.van ?? 0}
              subtitle="YOLO-World open-vocabulary detections"
              icon="🚐"
            />

            <ResultCard
              title="BUS/TRUCK UNCERTAIN"
              value={results.vehicles?.heavy_vehicle ?? 0}
              subtitle="Conflicting frame classifications"
              icon="🚛"
            />

            <ResultCard
              title="VEHICLE TYPE UNCERTAIN"
              value={results.vehicles?.uncertain_vehicle ?? 0}
              subtitle="Conflicting model classifications"
              icon="⚠️"
            />

            <ResultCard
              title="AUTO-RICKSHAWS"
              value={results.vehicles?.auto_rickshaw ?? 0}
              subtitle="Estimated from shape and color"
              icon="🛺"
            />

            <ResultCard
              title="YELLOW TAXIS"
              value={results.vehicles?.taxi ?? 0}
              subtitle="Estimated from shape and color"
              icon="🚕"
            />

            <ResultCard
              title="AMBULANCES"
              value={ambulanceAvailable
                ? results.vehicles?.ambulance ?? 0
                : ambulanceResultIsLegacy ? "Reanalyze video" : "Model needed"}
              subtitle={ambulanceAvailable
                ? ambulanceCapability.zero_shot
                  ? "YOLOv8s-World · zero-shot estimate"
                  : "Trained ambulance detector active"
                : ambulanceResultIsLegacy
                  ? "Restart backend, then upload this video again"
                  : ambulanceCapability?.reason || "Install ambulance detector"}
              icon="🚑"
            />

            <ResultCard
              title="LINE CROSSINGS"
              value={
                results.line_crossings ??
                results.vehicles_crossed ??
                0
              }
              subtitle="Vehicles crossed"
              icon="↕️"
            />

            <ResultCard
              title="AVERAGE SPEED"
              value={
                results.average_speed_kmh ??
                0
              }
              subtitle="km/h"
              icon="⚡"
            />

            <ResultCard
              title="SPEED VIOLATIONS"
              value={
                results.speed_violations ??
                0
              }
              subtitle={`Over ${
                results.speed_limit_kmh ??
                50
              } km/h`}
              icon="🚨"
            />

          </div>


          {roadCondition && (
            <section className="road-condition-panel" aria-labelledby="road-condition-title">
              <div className="road-condition-heading">
                <div>
                  <span className="eyebrow">ROAD CONDITIONS</span>
                  <h3 id="road-condition-title">Visual road check</h3>
                </div>
                <span className="road-condition-frames">
                  {roadCondition.frames_checked ?? 0} sampled frames
                </span>
              </div>
              <div className="road-condition-grid">
                <div className="road-condition-metric">
                  <span>ROAD SURFACE</span>
                  <strong>{roadSurfaceLabel}</strong>
                </div>
                <div className="road-condition-metric">
                  <span>VISIBILITY</span>
                  <strong>{roadCondition.visibility || "Not assessable"}</strong>
                </div>
                <div className="road-condition-metric">
                  <span>WET-SURFACE CUES</span>
                  <strong>
                    {typeof roadCondition.wet_surface_frame_ratio === "number"
                      ? `${Math.round(roadCondition.wet_surface_frame_ratio * 100)}% of samples`
                      : "Not available"}
                  </strong>
                </div>
              </div>
              <p className="road-condition-note">
                {roadConditionNote}
              </p>
            </section>
          )}


          {/* =================================================
              PROCESSED VIDEO
          ================================================= */}

          {results.video_url && (

            <div className="processed-video-panel">

              <div className="panel-header">

                <div>

                  <span className="eyebrow">
                    AI OUTPUT
                  </span>

                  <h3>
                    Annotated Traffic Video
                  </h3>

                  <p>
                    Vehicle boxes and tracking IDs stay on the video. Summary metrics and accident evidence are shown separately in this report and the Alerts page.
                  </p>

                </div>

                <a
                  href={`${API}${results.video_url}`}
                  target="_blank"
                  rel="noreferrer"
                  className="secondary-action"
                >
                  OPEN VIDEO ↗
                </a>

              </div>

              <video
                controls
                src={`${API}${results.video_url}`}
              />

            </div>

          )}

          <div className="analysis-incident-notice" role="status">
            <span aria-hidden="true">🚨</span>
            <div>
              <strong>
                {accidentEvents.length
                  ? `${accidentEvents.length} accident event${accidentEvents.length === 1 ? "" : "s"} saved as evidence`
                  : "Accident evidence is kept separate from the video"}
              </strong>
              <p>
                {accidentEvents.length
                  ? "Open Alerts to view each captured evidence frame and jump to its timestamp in the processed video."
                  : "Any confirmed accident detections and evidence frames will appear in Alerts."}
              </p>
            </div>
            <a href="/alerts">OPEN ALERTS →</a>
          </div>


          {/* =================================================
              HELMET ANALYSIS
          ================================================= */}

          <HelmetTable results={results} />

          {/* =================================================
              NUMBER PLATES
          ================================================= */}

          <PlateTable
            records={
              Array.isArray(results.vehicle_plates)
                ? results.vehicle_plates
                : (results.detected_plates || []).map((number_plate) => ({
                    vehicle_id: null,
                    vehicle: "unassigned",
                    number_plate,
                    reads: 1,
                    agreement: 0,
                  }))
            }
          />

        </section>

      )}

    </div>

  );
}
