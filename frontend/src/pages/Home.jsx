import React from "react";
import { Link } from "react-router-dom";

export default function Home() {
  return (
    <div className="home-page">

      <nav className="home-navbar">
        <div className="home-logo">
          <div className="home-logo-icon">🚦</div>

          <div>
            <strong>SMART TRAFFIC</strong>
            <span>AI COMMAND CENTER</span>
          </div>
        </div>

        <div className="home-nav-actions">
          <Link to="/login" className="home-login">
            LOGIN
          </Link>

          <Link to="/register" className="home-register">
            REGISTER →
          </Link>
        </div>
      </nav>

      <main className="home-hero">

        <div className="hero-content">

          <span className="hero-eyebrow">
            AI-POWERED TRAFFIC INTELLIGENCE
          </span>

          <h1>
            Smarter Roads.
            <br />
            <span>Safer Cities.</span>
          </h1>

          <p>
            An intelligent traffic management platform that uses
            computer vision and AI to detect vehicles, monitor
            traffic, analyze congestion and identify violations.
          </p>

          <div className="hero-buttons">
            <Link to="/login" className="hero-primary">
              ENTER COMMAND CENTER →
            </Link>

            <Link to="/register" className="hero-secondary">
              CREATE OFFICIAL ACCOUNT
            </Link>
          </div>

          <div className="hero-stats">

            <div>
              <strong>AI</strong>
              <span>Vehicle Detection</span>
            </div>

            <div>
              <strong>24/7</strong>
              <span>Traffic Monitoring</span>
            </div>

            <div>
              <strong>YOLO</strong>
              <span>Vision Engine</span>
            </div>

            <div>
              <strong>LIVE</strong>
              <span>Traffic Intelligence</span>
            </div>

          </div>

        </div>

        <div className="hero-visual">

          <div className="traffic-grid"></div>

          <div className="road-horizontal"></div>
          <div className="road-vertical"></div>

          <div className="traffic-light">
            <span className="light red"></span>
            <span className="light yellow"></span>
            <span className="light green"></span>
          </div>

          <div className="vehicle vehicle-1">🚗</div>
          <div className="vehicle vehicle-2">🚙</div>
          <div className="vehicle vehicle-3">🚌</div>
          <div className="vehicle vehicle-4">🚚</div>

          <div className="ai-detection detection-1">
            <span>CAR</span>
            <b>98%</b>
          </div>

          <div className="ai-detection detection-2">
            <span>BUS</span>
            <b>96%</b>
          </div>

          <div className="ai-detection detection-3">
            <span>TRUCK</span>
            <b>94%</b>
          </div>

          <div className="live-camera-label">
            <span className="status-dot"></span>
            LIVE AI VISION
          </div>

        </div>

      </main>

      <section className="home-features">

        <div className="feature-card">
          <span>01</span>
          <strong>AI Vehicle Detection</strong>
          <p>
            Automatically identify cars, motorcycles,
            buses and trucks.
          </p>
        </div>

        <div className="feature-card">
          <span>02</span>
          <strong>Intelligent Tracking</strong>
          <p>
            Track individual vehicles using persistent
            AI tracking IDs.
          </p>
        </div>

        <div className="feature-card">
          <span>03</span>
          <strong>Traffic Analytics</strong>
          <p>
            Understand congestion, vehicle flow,
            speed and road activity.
          </p>
        </div>

        <div className="feature-card">
          <span>04</span>
          <strong>Violation Detection</strong>
          <p>
            Detect speed violations and important
            traffic events automatically.
          </p>
        </div>

      </section>

    </div>
  );
}