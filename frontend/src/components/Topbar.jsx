import React from "react";
import { useNavigate } from "react-router-dom";

export default function Topbar({ animationsEnabled, onToggleAnimations }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("user");
    navigate("/", { replace: true });
  };

  return (
    <header className="topbar">
      <div>
        <span className="topbar-label">TRAFFIC INTELLIGENCE PLATFORM</span>
        <h1>Command Center</h1>
      </div>

      <div className="topbar-right">
        <button
          type="button"
          className={`motion-toggle ${animationsEnabled ? "is-on" : "is-off"}`}
          onClick={onToggleAnimations}
          aria-pressed={animationsEnabled}
          title={animationsEnabled ? "Turn animations off" : "Turn animations on"}
        >
          <span className="motion-toggle-indicator" aria-hidden="true">
            {animationsEnabled ? "✦" : "·"}
          </span>
          <span>Motion {animationsEnabled ? "On" : "Off"}</span>
        </button>

        <div className="live-status">
          <span className="status-dot"></span>
          SYSTEM ONLINE
        </div>

        <div className="topbar-time">
          AI ENGINE
          <strong>READY</strong>
        </div>

        <button
          type="button"
          className="logout-button"
          onClick={handleLogout}
          title="Log out and return to home"
        >
          <span aria-hidden="true">↪</span>
          LOG OUT
        </button>
      </div>
    </header>
  );
}
