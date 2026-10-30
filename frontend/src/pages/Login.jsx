import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setLoading(true);

    try {
      const response = await fetch(
        "http://localhost:5000/api/login",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: form.email,
            password: form.password,
          }),
        }
      );

      const contentType = response.headers.get("content-type");

      if (!contentType || !contentType.includes("application/json")) {
        throw new Error(
          `Backend returned an invalid response (${response.status}).`
        );
      }

      const data = await response.json();

      if (!response.ok) {
        setError(data.message || "Invalid email or password.");
        return;
      }

      // Store login information
      if (rememberMe) {
        localStorage.setItem("token", data.token);
        localStorage.setItem(
          "user",
          JSON.stringify(data.user)
        );
      } else {
        sessionStorage.setItem("token", data.token);
        sessionStorage.setItem(
          "user",
          JSON.stringify(data.user)
        );
      }

      // Login successful
      navigate("/dashboard");

    } catch (error) {
      console.error("LOGIN ERROR:", error);

      setError(
        error.message ||
        "Cannot connect to the server. Make sure the backend is running on port 5000."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = () => {
    alert("Password reset feature coming soon.");
  };

  return (
    <div className="auth-page">

      <div className="auth-card">

        {/* Logo */}
        <div className="auth-logo">
          🚦
        </div>

        {/* Heading */}
        <span className="eyebrow">
          OFFICIAL ACCESS
        </span>

        <h1>
          Welcome back
        </h1>

        <p>
          Sign in to access the Traffic Command Center.
        </p>

        <form onSubmit={handleSubmit}>

          {/* EMAIL */}
          <label htmlFor="email">
            OFFICIAL EMAIL
          </label>

          <input
            id="email"
            type="email"
            name="email"
            placeholder="official@example.com"
            value={form.email}
            onChange={handleChange}
            required
            autoComplete="email"
          />

          {/* PASSWORD */}
          <label htmlFor="password">
            PASSWORD
          </label>

          <div className="password-wrapper">

            <input
              id="password"
              type={showPassword ? "text" : "password"}
              name="password"
              placeholder="Enter password"
              value={form.password}
              onChange={handleChange}
              required
              autoComplete="current-password"
            />

            <button
              type="button"
              className="show-password"
              onClick={() =>
                setShowPassword(!showPassword)
              }
            >
              {showPassword ? "HIDE" : "SHOW"}
            </button>

          </div>

          {/* REMEMBER ME + FORGOT PASSWORD */}
          <div className="login-options">

            <label className="remember-option">

              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) =>
                  setRememberMe(e.target.checked)
                }
              />

              <span>
                REMEMBER ME
              </span>

            </label>

            <button
              type="button"
              className="forgot-password"
              onClick={handleForgotPassword}
            >
              Forgot password?
            </button>

          </div>

          {/* ERROR */}
          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          {/* LOGIN BUTTON */}
          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading
              ? "SIGNING IN..."
              : "SIGN IN TO COMMAND CENTER →"}
          </button>

        </form>

        {/* REGISTER */}
        <div className="auth-footer">
          Don't have an official account?

          {" "}

          <Link to="/register">
            CREATE ACCOUNT →
          </Link>
        </div>

        {/* SECURITY */}
        <div className="auth-security">

          <div className="security-icon">
            🔒
          </div>

          <div>
            <strong>
              SECURE OFFICIAL ACCESS
            </strong>

            <span>
              Authorized personnel only
            </span>
          </div>

        </div>

      </div>

    </div>
  );
}