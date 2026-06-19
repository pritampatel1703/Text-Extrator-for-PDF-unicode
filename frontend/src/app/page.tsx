"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type PlatformStats, type DocumentSummary } from "@/lib/api";
import { formatFileSize, formatRelativeTime, getStatusColor } from "@/lib/utils";

export default function DashboardPage() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [recentDocs, setRecentDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const [statsData, docsData] = await Promise.all([
        api.getStats().catch(() => null),
        api.getDocuments({ page: 1, page_size: 5 }).catch(() => null),
      ]);
      if (statsData) setStats(statsData);
      if (docsData) setRecentDocs(docsData.documents);
    } catch (e) {
      console.error("Dashboard load error:", e);
    } finally {
      setLoading(false);
    }
  }

  const statCards = [
    {
      label: "Total Documents",
      value: stats?.total_documents ?? 0,
      icon: "📄",
      color: "#7c3aed",
    },
    {
      label: "Pages Indexed",
      value: stats?.total_pages ?? 0,
      icon: "📑",
      color: "#a855f7",
    },
    {
      label: "Processing",
      value: stats?.processing_documents ?? 0,
      icon: "⚡",
      color: "#f59e0b",
    },
    {
      label: "Storage Used",
      value: formatFileSize(stats?.total_storage_bytes ?? 0),
      icon: "💾",
      color: "#10b981",
    },
  ];

  return (
    <div className="animate-fade-in">
      {/* Page Header */}
      <div style={{ marginBottom: "32px" }}>
        <h1
          style={{ fontSize: "28px", fontWeight: "800", marginBottom: "8px" }}
          className="gradient-text"
        >
          Dashboard
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "15px" }}>
          Overview of your PDF intelligence platform
        </p>
      </div>

      {/* Stats Grid */}
      <div
        className="stagger-children"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "20px",
          marginBottom: "32px",
        }}
      >
        {statCards.map((card) => (
          <div
            key={card.label}
            className="glass-card"
            style={{ padding: "24px" }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "16px",
              }}
            >
              <span style={{ fontSize: "28px" }}>{card.icon}</span>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "12px",
                  background: `${card.color}15`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: card.color,
                  }}
                />
              </div>
            </div>
            <p
              style={{
                fontSize: "32px",
                fontWeight: "800",
                letterSpacing: "-0.02em",
                marginBottom: "4px",
              }}
            >
              {loading ? (
                <span
                  className="skeleton"
                  style={{
                    display: "inline-block",
                    width: "80px",
                    height: "36px",
                  }}
                />
              ) : typeof card.value === "number" ? (
                card.value.toLocaleString()
              ) : (
                card.value
              )}
            </p>
            <p
              style={{
                fontSize: "13px",
                color: "var(--text-muted)",
                fontWeight: "500",
              }}
            >
              {card.label}
            </p>
          </div>
        ))}
      </div>

      {/* Quick Actions + Recent Documents */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "24px",
        }}
      >
        {/* Quick Actions */}
        <div className="glass-card" style={{ padding: "24px" }}>
          <h2
            style={{
              fontSize: "16px",
              fontWeight: "700",
              marginBottom: "20px",
              color: "var(--text-primary)",
            }}
          >
            Quick Actions
          </h2>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "12px",
            }}
          >
            <Link
              href="/upload"
              className="btn-primary"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                textDecoration: "none",
                padding: "14px",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Upload PDF Documents
            </Link>
            <Link
              href="/search"
              className="btn-secondary"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                textDecoration: "none",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              Search Documents
            </Link>
            <Link
              href="/documents"
              className="btn-secondary"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                textDecoration: "none",
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              Browse Library
            </Link>
          </div>
        </div>

        {/* Recent Documents */}
        <div className="glass-card" style={{ padding: "24px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "20px",
            }}
          >
            <h2
              style={{
                fontSize: "16px",
                fontWeight: "700",
                color: "var(--text-primary)",
              }}
            >
              Recent Uploads
            </h2>
            <Link
              href="/documents"
              style={{
                fontSize: "13px",
                color: "var(--accent-primary)",
                textDecoration: "none",
              }}
            >
              View all →
            </Link>
          </div>

          {loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="skeleton"
                  style={{ height: "52px", borderRadius: "var(--radius-md)" }}
                />
              ))}
            </div>
          ) : recentDocs.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {recentDocs.map((doc) => (
                <Link
                  key={doc.id}
                  href={`/documents/${doc.id}`}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 16px",
                    borderRadius: "var(--radius-md)",
                    background: "var(--bg-tertiary)",
                    textDecoration: "none",
                    transition: "all 0.2s",
                    border: "1px solid transparent",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = "var(--border-hover)";
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = "transparent";
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p
                      style={{
                        fontSize: "14px",
                        fontWeight: "500",
                        color: "var(--text-primary)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {doc.original_filename}
                    </p>
                    <p
                      style={{
                        fontSize: "12px",
                        color: "var(--text-muted)",
                        marginTop: "2px",
                      }}
                    >
                      {doc.page_count} pages •{" "}
                      {formatFileSize(doc.file_size)} •{" "}
                      {formatRelativeTime(doc.upload_date)}
                    </p>
                  </div>
                  <span
                    className={`badge ${
                      doc.processing_status === "completed"
                        ? "badge-success"
                        : doc.processing_status === "processing"
                        ? "badge-warning"
                        : doc.processing_status === "failed"
                        ? "badge-error"
                        : "badge-info"
                    }`}
                  >
                    {doc.processing_status}
                  </span>
                </Link>
              ))}
            </div>
          ) : (
            <div
              style={{
                textAlign: "center",
                padding: "32px",
                color: "var(--text-muted)",
              }}
            >
              <p style={{ fontSize: "14px" }}>No documents yet.</p>
              <Link
                href="/upload"
                style={{
                  color: "var(--accent-primary)",
                  fontSize: "14px",
                  textDecoration: "none",
                }}
              >
                Upload your first PDF →
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
