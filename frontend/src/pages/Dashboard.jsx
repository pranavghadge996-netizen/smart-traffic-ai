import React, { lazy, Suspense, useEffect, useRef, useState } from "react";
import StatCard from "../components/StatCard";

const CameraMap = lazy(() => import("../CameraMap"));

function DeferredCameraMap() {
  const containerRef = useRef(null);
  const [shouldLoad, setShouldLoad] = useState(false);

  useEffect(() => {
    if (shouldLoad || !containerRef.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShouldLoad(true);
          observer.disconnect();
        }
      },
      { rootMargin: "320px 0px" }
    );
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [shouldLoad]);

  return (
    <div ref={containerRef} className="camera-map-deferred">
      {shouldLoad ? (
        <Suspense fallback={<div className="camera-map-loading">Loading camera map…</div>}>
          <CameraMap />
        </Suspense>
      ) : (
        <div className="camera-map-loading">Camera map loads when you scroll to it</div>
      )}
    </div>
  );
}

export default function Dashboard() {
  return (
    <div className="page dashboard-page">

      {/* PAGE HEADER */}
      <div className="page-heading">
        <div>
          <span className="eyebrow">OVERVIEW</span>
          <h2>Traffic Command Center</h2>
          <p>
            Real-time AI-powered traffic intelligence and monitoring.
          </p>
        </div>

        <div className="dashboard-status">
          <span className="status-dot"></span>
          AI ENGINE ACTIVE
        </div>
      </div>


      {/* STAT CARDS */}
      <div className="stats-grid">

        <StatCard
          title="TOTAL VEHICLES"
          value="--"
          subtitle="Waiting for analysis"
          icon="🚗"
        />

        <StatCard
          title="CONGESTION"
          value="--"
          subtitle="Current traffic level"
          icon="🚦"
          type="warning"
        />

        <StatCard
          title="AVERAGE SPEED"
          value="--"
          subtitle="km/h"
          icon="⚡"
        />

        <StatCard
          title="VIOLATIONS"
          value="--"
          subtitle="Detected by AI"
          icon="⚠️"
          type="danger"
        />

      </div>


      {/* DASHBOARD GRID */}
      <div className="dashboard-grid">

        {/* QUICK ANALYSIS */}
        <section className="dashboard-panel quick-analysis">

          <div className="panel-header">
            <div>
              <span className="eyebrow">AI VISION</span>
              <h3>Quick Analysis</h3>
            </div>

            <span className="ai-badge">
              YOLO
            </span>
          </div>


          <div className="analysis-placeholder">

            <div className="analysis-icon">
              🎥
            </div>

            <h3>No analysis yet</h3>

            <p>
              Upload a traffic video to start real AI
              vehicle detection and tracking.
            </p>

            <a
              href="/analyze"
              className="primary-action"
            >
              ANALYZE VIDEO →
            </a>

          </div>

        </section>

      </div>


      {/* DASHBOARD BOTTOM */}
      <div className="dashboard-bottom">

        {/* SYSTEM STATUS */}
        <section className="dashboard-panel">

          <div className="panel-header">
            <div>
              <span className="eyebrow">SYSTEM</span>
              <h3>AI Engine Status</h3>
            </div>
          </div>


          <div className="system-list">

            <div className="system-row">

              <span className="system-name">
                YOLO Detection
              </span>

              <span className="system-online">
                ● READY
              </span>

            </div>


            <div className="system-row">

              <span className="system-name">
                ByteTrack Tracking
              </span>

              <span className="system-online">
                ● READY
              </span>

            </div>


            <div className="system-row">

              <span className="system-name">
                Video Processing
              </span>

              <span className="system-online">
                ● READY
              </span>

            </div>


          </div>

        </section>


        {/* CAPABILITIES */}
        <section className="dashboard-panel">

          <div className="panel-header">
            <div>
              <span className="eyebrow">PLATFORM</span>
              <h3>Capabilities</h3>
            </div>
          </div>


          <div className="capabilities">

            <div>
              <span>🚗</span>
              Vehicle Detection
            </div>

            <div>
              <span>🎯</span>
              Object Tracking
            </div>

            <div>
              <span>📊</span>
              Traffic Analytics
            </div>

            <div>
              <span>🚨</span>
              Speed Monitoring
            </div>

          </div>

        </section>

      </div>


      {/* REAL TRAFFIC CAMERA MAP */}
      <DeferredCameraMap />

    </div>
  );
}
