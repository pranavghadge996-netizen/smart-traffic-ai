import React from "react";

export default function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  type = "default",
}) {
  return (
    <div className={`stat-card ${type}`}>
      <div className="stat-card-top">
        <span className="stat-icon">{icon}</span>

        {trend && (
          <span className="stat-trend">
            {trend}
          </span>
        )}
      </div>

      <div className="stat-title">
        {title}
      </div>

      <div className="stat-value">
        {value}
      </div>

      {subtitle && (
        <div className="stat-subtitle">
          {subtitle}
        </div>
      )}
    </div>
  );
}