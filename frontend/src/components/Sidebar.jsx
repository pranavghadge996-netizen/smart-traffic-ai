
import React from "react";
import { NavLink } from "react-router-dom";

const menuItems = [
  {
    path: "/dashboard",
    icon: "⌂",
    label: "Dashboard",
  },
  {
    path: "/live",
    icon: "◉",
    label: "Live Monitoring",
  },
  {
    path: "/analyze",
    icon: "▶",
    label: "AI Analysis",
  },
  {
    path: "/analytics",
    icon: "▥",
    label: "Analytics",
  },
  {
    path: "/alerts",
    icon: "⚠",
    label: "Alerts",
  },
  {
    path: "/cameras",
    icon: "▣",
    label: "Cameras",
  },
  {
    path: "/reports",
    icon: "▤",
    label: "Reports",
  },
  {
    path: "/weather",
    icon: "☁",
    label: "Weather",
  },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      {/* BRAND */}
      <div className="brand">
        <div className="brand-icon">🚦</div>

        <div>
          <strong>SMART TRAFFIC</strong>
          <span>AI COMMAND CENTER</span>
        </div>
      </div>

      {/* NAVIGATION */}
      <div className="sidebar-section">
        <span className="sidebar-title">MONITORING</span>

        <nav>
          {menuItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* SIDEBAR BOTTOM */}
      <div className="sidebar-bottom">
        <div className="system-status">
          <span className="status-dot"></span>

          <div>
            <strong>System Online</strong>
            <span>AI Engine Ready</span>
          </div>
        </div>

        <div className="model-info">
          <span>VISION ENGINE</span>
          <b>YOLO + ByteTrack</b>
        </div>
      </div>
    </aside>
  );
}
