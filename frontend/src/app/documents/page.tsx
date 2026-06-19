"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type DocumentSummary, type DocumentListResponse } from "@/lib/api";
import { formatFileSize, formatDate, getLanguageName, getStatusColor } from "@/lib/utils";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [searchFilter, setSearchFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");

  useEffect(() => {
    loadDocuments();
  }, [page, statusFilter]);

  async function loadDocuments() {
    setLoading(true);
    try {
      const data = await api.getDocuments({
        page,
        page_size: 12,
        status: statusFilter || undefined,
        search: searchFilter || undefined,
      });
      setDocuments(data.documents);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (e) {
      console.error("Failed to load documents:", e);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string, filename: string) {
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    try {
      await api.deleteDocument(id);
      loadDocuments();
    } catch (e) {
      console.error("Delete failed:", e);
    }
  }

  return (
    <div className="animate-fade-in">
      {/* Page Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "32px",
        }}
      >
        <div>
          <h1
            style={{ fontSize: "28px", fontWeight: "800", marginBottom: "8px" }}
            className="gradient-text"
          >
            Document Library
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "15px" }}>
            {total} documents in your library
          </p>
        </div>
        <Link href="/upload" className="btn-primary" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: "8px" }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Upload
        </Link>
      </div>

      {/* Filters */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "24px",
          flexWrap: "wrap",
        }}
      >
        <input
          type="text"
          placeholder="Filter by filename..."
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && loadDocuments()}
          className="input"
          style={{ maxWidth: "300px" }}
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="input"
          style={{ maxWidth: "180px" }}
        >
          <option value="">All Status</option>
          <option value="completed">Completed</option>
          <option value="processing">Processing</option>
          <option value="pending">Pending</option>
          <option value="failed">Failed</option>
        </select>

        <div style={{ marginLeft: "auto", display: "flex", gap: "4px" }}>
          <button
            onClick={() => setViewMode("grid")}
            className="btn-secondary"
            style={{
              padding: "8px 12px",
              background: viewMode === "grid" ? "rgba(124, 58, 237, 0.12)" : undefined,
              borderColor: viewMode === "grid" ? "var(--accent-primary)" : undefined,
            }}
          >
            ▦
          </button>
          <button
            onClick={() => setViewMode("table")}
            className="btn-secondary"
            style={{
              padding: "8px 12px",
              background: viewMode === "table" ? "rgba(124, 58, 237, 0.12)" : undefined,
              borderColor: viewMode === "table" ? "var(--accent-primary)" : undefined,
            }}
          >
            ≡
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: viewMode === "grid" ? "repeat(auto-fill, minmax(300px, 1fr))" : "1fr",
            gap: "16px",
          }}
        >
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="skeleton"
              style={{
                height: viewMode === "grid" ? "160px" : "60px",
                borderRadius: "var(--radius-lg)",
              }}
            />
          ))}
        </div>
      )}

      {/* Grid View */}
      {!loading && viewMode === "grid" && (
        <div
          className="stagger-children"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: "16px",
          }}
        >
          {documents.map((doc) => (
            <div key={doc.id} className="glass-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "12px" }}>
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "12px",
                    background: "rgba(239, 68, 68, 0.1)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: "12px", fontWeight: "800", color: "#ef4444" }}>PDF</span>
                </div>
                <span
                  className={`badge ${
                    doc.processing_status === "completed" ? "badge-success"
                    : doc.processing_status === "processing" ? "badge-warning"
                    : doc.processing_status === "failed" ? "badge-error"
                    : "badge-info"
                  }`}
                >
                  {doc.processing_status}
                </span>
              </div>

              <Link
                href={`/documents/${doc.id}`}
                style={{
                  textDecoration: "none",
                  fontSize: "15px",
                  fontWeight: "600",
                  color: "var(--text-primary)",
                  display: "block",
                  marginBottom: "8px",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                {doc.original_filename}
              </Link>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "12px",
                  fontSize: "12px",
                  color: "var(--text-muted)",
                  marginBottom: "16px",
                }}
              >
                <span>{doc.page_count} pages</span>
                <span>{formatFileSize(doc.file_size)}</span>
                {doc.primary_language && (
                  <span>{getLanguageName(doc.primary_language)}</span>
                )}
              </div>

              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                  {formatDate(doc.upload_date)}
                </span>
                <div style={{ display: "flex", gap: "4px" }}>
                  <Link
                    href={`/documents/${doc.id}`}
                    className="btn-secondary"
                    style={{ padding: "4px 12px", fontSize: "12px", textDecoration: "none" }}
                  >
                    View
                  </Link>
                  <button
                    onClick={() => handleDelete(doc.id, doc.original_filename)}
                    style={{
                      padding: "4px 12px",
                      fontSize: "12px",
                      borderRadius: "var(--radius-md)",
                      border: "1px solid rgba(239, 68, 68, 0.3)",
                      background: "rgba(239, 68, 68, 0.05)",
                      color: "var(--error)",
                      cursor: "pointer",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Table View */}
      {!loading && viewMode === "table" && (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Document</th>
                <th>Pages</th>
                <th>Size</th>
                <th>Language</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>
                    <Link href={`/documents/${doc.id}`} style={{ color: "var(--text-primary)", textDecoration: "none", fontWeight: "500" }}>
                      {doc.original_filename}
                    </Link>
                  </td>
                  <td>{doc.page_count}</td>
                  <td>{formatFileSize(doc.file_size)}</td>
                  <td>{doc.primary_language ? getLanguageName(doc.primary_language) : "—"}</td>
                  <td>
                    <span
                      className={`badge ${
                        doc.processing_status === "completed" ? "badge-success"
                        : doc.processing_status === "processing" ? "badge-warning"
                        : doc.processing_status === "failed" ? "badge-error"
                        : "badge-info"
                      }`}
                    >
                      {doc.processing_status}
                    </span>
                  </td>
                  <td style={{ fontSize: "13px", color: "var(--text-muted)" }}>{formatDate(doc.upload_date)}</td>
                  <td>
                    <button
                      onClick={() => handleDelete(doc.id, doc.original_filename)}
                      style={{
                        padding: "4px 10px",
                        fontSize: "12px",
                        borderRadius: "6px",
                        border: "none",
                        background: "rgba(239, 68, 68, 0.1)",
                        color: "var(--error)",
                        cursor: "pointer",
                      }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Empty State */}
      {!loading && documents.length === 0 && (
        <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)" }}>
          <p style={{ fontSize: "48px", marginBottom: "16px" }}>📁</p>
          <p style={{ fontSize: "18px", fontWeight: "600", marginBottom: "8px", color: "var(--text-secondary)" }}>
            No documents found
          </p>
          <Link href="/upload" style={{ color: "var(--accent-primary)", textDecoration: "none" }}>
            Upload your first PDF →
          </Link>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", gap: "8px", marginTop: "32px" }}>
          <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)} style={{ padding: "8px 16px", fontSize: "13px" }}>
            ← Previous
          </button>
          <span style={{ padding: "8px 16px", fontSize: "13px", color: "var(--text-secondary)" }}>
            Page {page} of {totalPages}
          </span>
          <button className="btn-secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)} style={{ padding: "8px 16px", fontSize: "13px" }}>
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
