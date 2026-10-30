import React from "react";

const vehicleData = [
  { name: "Cars", value: 0, icon: "🚗" },
  { name: "Motorcycles", value: 0, icon: "🏍️" },
  { name: "Buses", value: 0, icon: "🚌" },
  { name: "Trucks", value: 0, icon: "🚚" },
  { name: "Yellow taxis", value: 0, icon: "🚕" },
  { name: "Auto-rickshaws", value: 0, icon: "🛺" },
];

export default function Analytics() {
  return (
    <div className="page analytics-page">
      <div className="page-heading">
        <div>
          <span className="eyebrow">TRAFFIC ANALYTICS</span>
          <h2>Intelligence & Insights</h2>
          <p>
            Analyze vehicle flow, congestion, speed and lane activity.
          </p>
        </div>

        <div className="dashboard-status">
          <span className="status-dot"></span>
          ANALYTICS ENGINE READY
        </div>
      </div>

      <div className="analytics-summary">
        <div className="analytics-summary-card">
          <span>TOTAL VEHICLES</span>
          <strong>--</strong>
          <small>From latest analysis</small>
        </div>

        <div className="analytics-summary-card">
          <span>AVERAGE SPEED</span>
          <strong>--</strong>
          <small>km/h</small>
        </div>

        <div className="analytics-summary-card">
          <span>LINE CROSSINGS</span>
          <strong>--</strong>
          <small>Tracked vehicles</small>
        </div>

        <div className="analytics-summary-card">
          <span>CONGESTION</span>
          <strong>--</strong>
          <small>AI calculated</small>
        </div>
      </div>

      <div className="analytics-grid">

        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">VEHICLE MIX</span>
              <h3>Vehicle Classification</h3>
            </div>
          </div>

          <div className="vehicle-bars">
            {vehicleData.map((vehicle) => (
              <div className="vehicle-bar-row" key={vehicle.name}>
                <div className="vehicle-bar-label">
                  <span>
                    <span className="vehicle-type-icon" aria-hidden="true">{vehicle.icon}</span>
                    {vehicle.name}
                  </span>

                  <strong>{vehicle.value}</strong>
                </div>

                <div className="vehicle-bar-track">
                  <div
                    className="vehicle-bar-fill"
                    style={{
                      width: `${vehicle.value}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="analytics-note">
            Vehicle distribution will be populated from the
            latest real AI video analysis.
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">LANE ANALYSIS</span>
              <h3>Traffic Distribution</h3>
            </div>
          </div>

          <div className="lane-visual">

            <div className="lane">
              <span>LEFT LANE</span>
              <strong>--</strong>
              <small>vehicles</small>
            </div>

            <div className="lane-divider"></div>

            <div className="lane">
              <span>RIGHT LANE</span>
              <strong>--</strong>
              <small>vehicles</small>
            </div>

          </div>

          <div className="lane-status">
            <span className="status-dot"></span>
            Waiting for analysis data
          </div>
        </section>

      </div>

      <section className="dashboard-panel speed-panel">

        <div className="panel-header">
          <div>
            <span className="eyebrow">SPEED INTELLIGENCE</span>
            <h3>Vehicle Speed Analysis</h3>
          </div>

          <span className="ai-badge">
            AI MEASURED
          </span>
        </div>

        <div className="speed-dashboard">

          <div className="speed-gauge">
            <div className="gauge-inner">
              <span>AVERAGE</span>
              <strong>--</strong>
              <small>km/h</small>
            </div>
          </div>

          <div className="speed-info">

            <div className="speed-info-row">
              <span>Speed Limit</span>
              <strong>-- km/h</strong>
            </div>

            <div className="speed-info-row">
              <span>Violations</span>
              <strong>--</strong>
            </div>

            <div className="speed-info-row">
              <span>Traffic Condition</span>
              <strong>--</strong>
            </div>

          </div>

        </div>

      </section>

      <div className="analytics-bottom">

        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">CONGESTION ENGINE</span>
              <h3>Traffic Health</h3>
            </div>
          </div>

          <div className="congestion-meter">

            <div className="meter-track">
              <div className="meter-fill"></div>
            </div>

            <div className="meter-labels">
              <span>LOW</span>
              <span>MEDIUM</span>
              <span>HIGH</span>
            </div>

          </div>

          <div className="congestion-message">
            <span className="status-dot"></span>
            Upload a video to calculate congestion.
          </div>
        </section>

        <section className="dashboard-panel">
          <div className="panel-header">
            <div>
              <span className="eyebrow">DATA SOURCE</span>
              <h3>Current Dataset</h3>
            </div>
          </div>

          <div className="dataset-info">
            <div>
              <span>MODEL</span>
              <strong>YOLO</strong>
            </div>

            <div>
              <span>TRACKER</span>
              <strong>ByteTrack</strong>
            </div>

            <div>
              <span>INPUT</span>
              <strong>Traffic Video</strong>
            </div>
          </div>
        </section>

      </div>
    </div>
  );
}
