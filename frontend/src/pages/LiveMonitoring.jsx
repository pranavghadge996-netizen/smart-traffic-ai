import React from "react";

export default function LiveMonitoring() {
  return (
    <div className="page live-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">LIVE MONITORING</span>
          <h2>Traffic Camera Network</h2>
          <p>
            Monitor AI-powered vehicle detection and tracking.
          </p>
        </div>

        <div className="dashboard-status">
          <span className="status-dot"></span>
          AI MONITORING READY
        </div>
      </div>

      <div className="camera-toolbar">
        <div className="camera-selector">
          <span>CAMERA</span>
          <select>
            <option>Camera 01 — Main Junction</option>
            <option>Camera 02 — Highway</option>
            <option>Camera 03 — City Road</option>
            <option>Camera 04 — Exit Road</option>
          </select>
        </div>

        <div className="camera-status">
          <span className="status-dot"></span>
          ONLINE
        </div>
      </div>

      <section className="live-video-panel">
        <div className="video-placeholder">
          <div className="video-grid"></div>

          <div className="camera-overlay top-left">
            <span>CAM 01</span>
            <b>LIVE</b>
          </div>

          <div className="camera-overlay top-right">
            YOLO + BYTETRACK
          </div>

          <div className="video-center">
            <div className="play-circle">▶</div>
            <h3>No active video stream</h3>
            <p>
              Upload a traffic video from the AI Analysis page
              to process real vehicle tracking data.
            </p>

            <a href="/analyze" className="primary-action">
              OPEN AI ANALYSIS →
            </a>
          </div>

          <div className="camera-overlay bottom-left">
            FPS <strong>--</strong>
          </div>

          <div className="camera-overlay bottom-right">
            TRACKING <strong>READY</strong>
          </div>
        </div>
      </section>

      <div className="live-stats-grid">
        <div className="live-stat">
          <span>ACTIVE VEHICLES</span>
          <strong>--</strong>
          <small>Waiting for video</small>
        </div>

        <div className="live-stat">
          <span>TRACKED IDS</span>
          <strong>--</strong>
          <small>ByteTrack</small>
        </div>

        <div className="live-stat">
          <span>AVERAGE SPEED</span>
          <strong>--</strong>
          <small>km/h</small>
        </div>

        <div className="live-stat">
          <span>CONGESTION</span>
          <strong>--</strong>
          <small>AI calculated</small>
        </div>
      </div>

      <div className="live-bottom-grid">
        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">DETECTION ENGINE</span>
              <h3>Vehicle Classes</h3>
            </div>
          </div>

          <div className="vehicle-class-list">
            <div>
              <span>🚗 Cars</span>
              <b>--</b>
            </div>

            <div>
              <span>🏍️ Motorcycles</span>
              <b>--</b>
            </div>

            <div>
              <span>🚌 Buses</span>
              <b>--</b>
            </div>

            <div>
              <span>🚚 Trucks</span>
              <b>--</b>
            </div>
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">TRACKING ENGINE</span>
              <h3>AI Status</h3>
            </div>
          </div>

          <div className="tracking-status">
            <div className="tracking-item">
              <span className="status-dot"></span>
              YOLO Object Detection
              <b>READY</b>
            </div>

            <div className="tracking-item">
              <span className="status-dot"></span>
              ByteTrack Tracking
              <b>READY</b>
            </div>

            <div className="tracking-item">
              <span className="status-dot"></span>
              Vehicle Classification
              <b>READY</b>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}