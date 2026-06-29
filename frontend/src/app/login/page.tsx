"use client";

import { useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import Link from "next/link";

export default function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(username, password);
      window.location.href = "/";
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  }

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
        <div style={{ textAlign: "center", marginBottom: "36px" }}>
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
            📄
          </div>
          <h1
            style={{
              fontSize: "24px",
              fontWeight: "800",
              marginBottom: "8px",
            }}
          >
            Welcome Back
          </h1>
          <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>
            Sign in to your PDF Search Platform
          </p>
        </div>

        {/* Error Message */}
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

        {/* Login Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label
              htmlFor="username"
              style={{
                display: "block",
                fontSize: "13px",
                fontWeight: "600",
                color: "var(--text-secondary)",
                marginBottom: "6px",
              }}
            >
              Username or Email
            </label>
            <input
              id="username"
              type="text"
              className="input"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              autoComplete="username"
            />
          </div>

          <div>
            <label
              htmlFor="password"
              style={{
                display: "block",
                fontSize: "13px",
                fontWeight: "600",
                color: "var(--text-secondary)",
                marginBottom: "6px",
              }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              className="input"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !username || !password}
            style={{
              marginTop: "8px",
              padding: "14px",
              fontSize: "15px",
              fontWeight: "700",
              opacity: loading || !username || !password ? 0.6 : 1,
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
                Signing in...
              </span>
            ) : (
              "Sign In"
            )}
          </button>
        </form>

        {/* Footer */}
        <div style={{ textAlign: "center", marginTop: "28px" }}>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Don&apos;t have an account?{" "}
            <Link
              href="/register"
              style={{
                color: "var(--accent-secondary)",
                fontWeight: "600",
                textDecoration: "none",
              }}
            >
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
