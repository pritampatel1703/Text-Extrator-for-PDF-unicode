"use client";

import { useEffect, useState } from "react";
import { api, type PlatformStats } from "@/lib/api";
import { formatFileSize } from "@/lib/utils";

export default function AdminPage() {
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [health, setHealth] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAdmin();
  }, []);

  async function loadAdmin() {
    try {
      const [statsData, healthData] = await Promise.all([
        api.getStats().catch(() => null),
        api.healthCheck().catch(() => ({ status: "error", elasticsearch: "unknown" })),
      ]);
      if (statsData) setStats(statsData);
      setHealth(healthData as Record<string, string>);
    } catch (e) {
      console.error("Admin load error:", e);
    } finally {
      setLoading(false);
    }
  }

  const services = [
    {
      name: "API Server",
      status: health.status === "healthy" ? "online" : "offline",
      icon: "🖥️",
    },
    {
      name: "Elasticsearch",
      status: health.elasticsearch === "healthy" ? "online" : "offline",
      icon: "🔍",
    },
    {
      name: "PostgreSQL",
      status: health.status === "healthy" ? "online" : "unknown",
      icon: "🗄️",
    },
    {
      name: "Redis",
      status: health.status === "healthy" ? "online" : "unknown",
      icon: "⚡",
    },
    {
      name: "Celery Workers",
      status: "active",
      icon: "⚙️",
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
          Admin Panel
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "15px" }}>
          System monitoring, health checks, and configuration
        </p>
      </div>

      {/* System Health */}
      <div className="glass-card" style={{ padding: "24px", marginBottom: "24px" }}>
        <h2 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "20px" }}>
          System Health
        </h2>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: "16px",
          }}
        >
          {services.map((service) => (
            <div
              key={service.name}
              style={{
                padding: "16px",
                borderRadius: "var(--radius-md)",
                background: "var(--bg-tertiary)",
                border: "1px solid var(--border-color)",
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <span style={{ fontSize: "24px" }}>{service.icon}</span>
              <div>
                <p style={{ fontSize: "14px", fontWeight: "600" }}>{service.name}</p>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px" }}>
                  <div
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background:
                        service.status === "online" || service.status === "active"
                          ? "var(--success)"
                          : service.status === "unknown"
                          ? "var(--warning)"
                          : "var(--error)",
                    }}
                  />
                  <span
                    style={{
                      fontSize: "12px",
                      color:
                        service.status === "online" || service.status === "active"
                          ? "var(--success)"
                          : service.status === "unknown"
                          ? "var(--warning)"
                          : "var(--error)",
                      fontWeight: "500",
                      textTransform: "capitalize",
                    }}
                  >
                    {service.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Platform Statistics */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "24px",
        }}
      >
        <div className="glass-card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "20px" }}>
            Platform Statistics
          </h2>
          {stats ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <StatRow label="Total Documents" value={stats.total_documents.toLocaleString()} />
              <StatRow label="Total Pages" value={stats.total_pages.toLocaleString()} />
              <StatRow label="Completed" value={stats.completed_documents.toLocaleString()} />
              <StatRow label="Processing" value={stats.processing_documents.toLocaleString()} />
              <StatRow label="Pending" value={stats.pending_documents.toLocaleString()} />
              <StatRow label="Total Storage" value={formatFileSize(stats.total_storage_bytes)} />
            </div>
          ) : (
            <p style={{ color: "var(--text-muted)" }}>Loading...</p>
          )}
        </div>

        <div className="glass-card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "16px", fontWeight: "700", marginBottom: "20px" }}>
            Configuration
          </h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <StatRow label="API Version" value="v1.0.0" />
            <StatRow label="Environment" value={health.environment || "development"} />
            <StatRow label="Max Upload Size" value="200 MB" />
            <StatRow label="OCR Engine" value="PaddleOCR" />
            <StatRow label="Embedding Model" value="BGE-M3" />
            <StatRow label="Search Engine" value="Elasticsearch 8.x" />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "8px 0",
        borderBottom: "1px solid var(--border-color)",
      }}
    >
      <span style={{ fontSize: "13px", color: "var(--text-muted)" }}>{label}</span>
      <span style={{ fontSize: "14px", fontWeight: "600", color: "var(--text-primary)" }}>
        {value}
      </span>
    </div>
  );
}
