
import React, { lazy, Suspense, useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";

const Home = lazy(() => import("./pages/Home"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const LiveMonitoring = lazy(() => import("./pages/LiveMonitoring"));
const AIAnalysis = lazy(() => import("./pages/AIAnalysis"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Alerts = lazy(() => import("./pages/Alerts"));
const Cameras = lazy(() => import("./pages/Cameras"));
const Reports = lazy(() => import("./pages/Reports"));
const Weather = lazy(() => import("./pages/Weather"));

const MOTION_STORAGE_KEY = "smartTrafficAI.animationsEnabled";

function getInitialMotionPreference() {
  try {
    const saved = localStorage.getItem(MOTION_STORAGE_KEY);
    if (saved !== null) return saved === "true";
    return !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return true;
  }
}

function CommandCenter({ animationsEnabled, onToggleAnimations }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div
      className={`app-shell ${
        sidebarOpen ? "sidebar-open" : "sidebar-closed"
      }`}
    >
      <Sidebar />

      <div className="main-area">
        <Topbar
          setSidebarOpen={setSidebarOpen}
          animationsEnabled={animationsEnabled}
          onToggleAnimations={onToggleAnimations}
        />

        <main className="content-area">
          <Suspense fallback={<div className="page-loading" role="status">Loading page…</div>}>
          <Routes>
            {/* Dashboard */}
            <Route
              path="/dashboard"
              element={<Dashboard />}
            />

            {/* Live Monitoring */}
            <Route
              path="/live"
              element={<LiveMonitoring />}
            />

            {/* AI Analysis */}
            <Route
              path="/analyze"
              element={<AIAnalysis />}
            />

            {/* Analytics */}
            <Route
              path="/analytics"
              element={<Analytics />}
            />

            {/* Alerts */}
            <Route
              path="/alerts"
              element={<Alerts />}
            />

            {/* Cameras */}
            <Route
              path="/cameras"
              element={<Cameras />}
            />

            {/* Reports */}
            <Route
              path="/reports"
              element={<Reports />}
            />

            {/* Weather & Road Hazard Alerts */}
            <Route
              path="/weather"
              element={<Weather />}
            />

            {/* Unknown command-center URL */}
            <Route
              path="*"
              element={
                <Navigate
                  to="/dashboard"
                  replace
                />
              }
            />
          </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  const [animationsEnabled, setAnimationsEnabled] = useState(getInitialMotionPreference);

  const toggleAnimations = () => {
    const next = !animationsEnabled;
    setAnimationsEnabled(next);
    try {
      localStorage.setItem(MOTION_STORAGE_KEY, String(next));
    } catch (error) {
      console.warn("Unable to save animation preference:", error);
    }
  };

  return (
    <div className="app-root" data-motion={animationsEnabled ? "on" : "off"}>
      <BrowserRouter>
        <Suspense fallback={<div className="page-loading" role="status">Loading page…</div>}>
        <Routes>
          {/* Public Pages */}
          <Route
            path="/"
            element={<Home />}
          />

          <Route
            path="/login"
            element={<Login />}
          />

          <Route
            path="/register"
            element={<Register />}
          />

          {/* Command Center */}
          <Route
            path="/*"
            element={
              <CommandCenter
                animationsEnabled={animationsEnabled}
                onToggleAnimations={toggleAnimations}
              />
            }
          />
        </Routes>
        </Suspense>
      </BrowserRouter>
    </div>
  );
}
