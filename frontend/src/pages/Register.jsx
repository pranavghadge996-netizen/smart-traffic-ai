import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Register() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "Traffic Official",
  });

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
        "http://localhost:5000/api/register",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(form),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setError(data.message || "Registration failed");
        setLoading(false);
        return;
      }

      alert("Registration successful!");

      navigate("/login");
    } catch (error) {
      console.error(error);
      setError(
        "Cannot connect to backend. Make sure server.js is running."
      );
    }

    setLoading(false);
  };

  return (
    <div className="auth-page">

      <div className="auth-card">

        <div className="auth-logo">
          🚦
        </div>

        <span className="eyebrow">
          SMART TRAFFIC AI
        </span>

        <h1>Create Official Account</h1>

        <p>
          Register to access the Traffic Intelligence Command Center.
        </p>

        {error && (
          <div className="auth-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>

          <div className="form-group">
            <label>FULL NAME</label>

            <input
              type="text"
              name="name"
              placeholder="Enter your full name"
              value={form.name}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label>OFFICIAL EMAIL</label>

            <input
              type="email"
              name="email"
              placeholder="Enter official email"
              value={form.email}
              onChange={handleChange}
              required
            />
          </div>

          <div className="form-group">
            <label>ROLE</label>

            <select
              name="role"
              value={form.role}
              onChange={handleChange}
            >
              <option>Traffic Official</option>
              <option>Traffic Police</option>
              <option>Traffic Controller</option>
              <option>Administrator</option>
            </select>
          </div>

          <div className="form-group">
            <label>PASSWORD</label>

            <input
              type="password"
              name="password"
              placeholder="Create password"
              value={form.password}
              onChange={handleChange}
              required
              minLength="6"
            />
          </div>

          <button
            type="submit"
            className="auth-button"
            disabled={loading}
          >
            {loading
              ? "CREATING ACCOUNT..."
              : "CREATE ACCOUNT →"}
          </button>

        </form>

        <div className="auth-footer">
          Already have an account?

          {" "}

          <Link to="/login">
            Login
          </Link>
        </div>

        <Link to="/" className="back-home">
          ← Back to Home
        </Link>

      </div>

    </div>
  );
}