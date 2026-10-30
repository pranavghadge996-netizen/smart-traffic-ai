import React from "react";

const cameras = [
  {
    id: "CAM-01",
    name: "Main Junction",
    location: "Central Road",
    status: "ONLINE",
    traffic: "NORMAL",
  },
  {
    id: "CAM-02",
    name: "Highway Entry",
    location: "North Highway",
    status: "ONLINE",
    traffic: "MEDIUM",
  },
  {
    id: "CAM-03",
    name: "City Road",
    location: "Downtown",
    status: "ONLINE",
    traffic: "LOW",
  },
  {
    id: "CAM-04",
    name: "Exit Road",
    location: "South Exit",
    status: "READY",
    traffic: "UNKNOWN",
  },
];

export default function Cameras() {
  return (
    <div className="page cameras-page">

      <div className="page-heading">
        <div>
          <span className="eyebrow">CAMERA NETWORK</span>

          <h2>Traffic Cameras</h2>

          <p>
            Manage monitoring points and AI traffic
            detection sources.
          </p>
        </div>

        <div className="dashboard-status">
          <span className="status-dot"></span>
          NETWORK READY
        </div>
      </div>

      <div className="camera-summary">

        <div>
          <span>CAMERAS</span>
          <strong>04</strong>
          <small>Configured</small>
        </div>

        <div>
          <span>ONLINE</span>
          <strong>03</strong>
          <small>Available sources</small>
        </div>

        <div>
          <span>AI ENGINE</span>
          <strong>READY</strong>
          <small>YOLO + ByteTrack</small>
        </div>

        <div>
          <span>STREAM</span>
          <strong>--</strong>
          <small>Live video</small>
        </div>

      </div>

      <div className="camera-grid">

        {cameras.map((camera) => (
          <section
            className="camera-card"
            key={camera.id}
          >

            <div className="camera-preview">

              <div className="camera-grid-lines"></div>

              <div className="camera-preview-top">
                <span>{camera.id}</span>

                <b
                  className={
                    camera.status === "ONLINE"
                      ? "online-badge"
                      : "ready-badge"
                  }
                >
                  ● {camera.status}
                </b>
              </div>

              <div className="camera-placeholder">
                <span>📹</span>
                <small>NO LIVE STREAM</small>
              </div>

              <div className="camera-preview-bottom">
                AI VISION READY
              </div>

            </div>

            <div className="camera-card-info">

              <div>
                <span className="eyebrow">
                  {camera.id}
                </span>

                <h3>{camera.name}</h3>

                <p>📍 {camera.location}</p>
              </div>

              <div
                className={`traffic-indicator ${camera.traffic.toLowerCase()}`}
              >
                {camera.traffic}
              </div>

            </div>

            <div className="camera-card-footer">

              <span>
                YOLO Detection
              </span>

              <span>
                ByteTrack
              </span>

              <button>
                VIEW CAMERA →
              </button>

            </div>

          </section>
        ))}

      </div>

      <section className="dashboard-panel camera-network-panel">

        <div className="panel-header">

          <div>
            <span className="eyebrow">
              NETWORK CONFIGURATION
            </span>

            <h3>AI Monitoring Pipeline</h3>
          </div>

          <span className="ai-badge">
            READY
          </span>

        </div>

        <div className="camera-pipeline">

          <div className="pipeline-step">
            <span>01</span>
            <strong>Camera Input</strong>
            <small>
              Road / CCTV video
            </small>
          </div>

          <div className="pipeline-arrow">
            →
          </div>

          <div className="pipeline-step">
            <span>02</span>
            <strong>YOLO Detection</strong>
            <small>
              Vehicle recognition
            </small>
          </div>

          <div className="pipeline-arrow">
            →
          </div>

          <div className="pipeline-step">
            <span>03</span>
            <strong>ByteTrack</strong>
            <small>
              Persistent IDs
            </small>
          </div>

          <div className="pipeline-arrow">
            →
          </div>

          <div className="pipeline-step">
            <span>04</span>
            <strong>Analytics</strong>
            <small>
              Traffic intelligence
            </small>
          </div>

        </div>

      </section>

    </div>
  );
}