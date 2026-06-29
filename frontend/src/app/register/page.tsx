"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

export default function RegisterPage() {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    full_name: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function updateField(field: string, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (formData.password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);

    try {
      await register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.full_name || undefined,
      });
      window.location.href = "/";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const isFormValid =
    formData.username && formData.email && formData.password && formData.confirmPassword;

  return (
    <div
      className="bg-mesh"
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <div
        className="animate-fade-in glass-card"
        style={{
          width: "100%",
          maxWidth: "440px",
          padding: "48px 40px",
        }}
      >
        {/* Logo / Brand */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "16px",
              background: "var(--accent-gradient)",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "28px",
              marginBottom: "20px",
              boxShadow: "0 0 30px var(--accent-glow)",
            }}
          >
            🚀
          </div>
          <h1 style={{ fontSize: "24px", fontWeight: "800", marginBottom: "8px" }}>
            Create Account
          </h1>
          <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>
            Get started with PDF Search Platform
          </p>
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              padding: "12px 16px",
              borderRadius: "var(--radius-md)",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              color: "var(--error)",
              fontSize: "13px",
              marginBottom: "20px",
              textAlign: "center",
            }}
          >
            {error}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div>
            <label
              htmlFor="full_name"
              style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "6px" }}
            >
              Full Name <span style={{ color: "var(--text-muted)", fontWeight: "400" }}>(optional)</span>
            </label>
            <input
              id="full_name"
              type="text"
              className="input"
              placeholder="John Doe"
              value={formData.full_name}
              onChange={(e) => updateField("full_name", e.target.value)}
              autoComplete="name"
            />
          </div>

          <div>
            <label
              htmlFor="reg-username"
              style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "6px" }}
            >
              Username
            </label>
            <input
              id="reg-username"
              type="text"
              className="input"
              placeholder="Choose a username"
              value={formData.username}
              onChange={(e) => updateField("username", e.target.value)}
              required
              autoFocus
              autoComplete="username"
            />
          </div>

          <div>
            <label
              htmlFor="reg-email"
              style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "6px" }}
            >
              Email
            </label>
            <input
              id="reg-email"
              type="email"
              className="input"
              placeholder="you@example.com"
              value={formData.email}
              onChange={(e) => updateField("email", e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div>
            <label
              htmlFor="reg-password"
              style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "6px" }}
            >
              Password
            </label>
            <input
              id="reg-password"
              type="password"
              className="input"
              placeholder="Min. 8 characters"
              value={formData.password}
              onChange={(e) => updateField("password", e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>

          <div>
            <label
              htmlFor="reg-confirm-password"
              style={{ display: "block", fontSize: "13px", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "6px" }}
            >
              Confirm Password
            </label>
            <input
              id="reg-confirm-password"
              type="password"
              className="input"
              placeholder="Repeat your password"
              value={formData.confirmPassword}
              onChange={(e) => updateField("confirmPassword", e.target.value)}
              required
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !isFormValid}
            style={{
              marginTop: "8px",
              padding: "14px",
              fontSize: "15px",
              fontWeight: "700",
              opacity: loading || !isFormValid ? 0.6 : 1,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? (
              <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                <span
                  style={{
                    width: "16px",
                    height: "16px",
                    border: "2px solid rgba(255,255,255,0.3)",
                    borderTopColor: "white",
                    borderRadius: "50%",
                    display: "inline-block",
                    animation: "spin-slow 0.8s linear infinite",
                  }}
                />
                Creating account...
              </span>
            ) : (
              "Create Account"
            )}
          </button>
        </form>

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: "24px" }}>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Already have an account?{" "}
            <Link
              href="/login"
              style={{
                color: "var(--accent-secondary)",
                fontWeight: "600",
                textDecoration: "none",
              }}
            >
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
