"use client";

import { useCallback, useState, useRef } from "react";
import { api, type UploadResponse } from "@/lib/api";
import { formatFileSize, cn } from "@/lib/utils";

interface UploadFile {
  id: string;
  file: File;
  progress: number;
  status: "pending" | "uploading" | "processing" | "completed" | "failed";
  error?: string;
  documentId?: string;
}

export default function UploadPage() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    const uploadFiles: UploadFile[] = fileArray
      .filter((f) => f.name.toLowerCase().endsWith(".pdf"))
      .filter((f) => f.size <= 200 * 1024 * 1024) // 200MB limit
      .map((f) => ({
        id: Math.random().toString(36).substring(2),
        file: f,
        progress: 0,
        status: "pending" as const,
      }));

    if (uploadFiles.length < fileArray.length) {
      alert("Some files were skipped (not PDF or too large).");
    }

    setFiles((prev) => [...prev, ...uploadFiles]);
  }, []);

  const uploadFile = async (uploadFile: UploadFile) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === uploadFile.id ? { ...f, status: "uploading" } : f
      )
    );

    try {
      const result = await api.uploadPdf(uploadFile.file, (progress) => {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id ? { ...f, progress } : f
          )
        );
      });

      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? {
                ...f,
                status: "completed",
                progress: 100,
                documentId: result.document_id,
              }
            : f
        )
      );
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : "Upload failed";
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? { ...f, status: "failed", error: errorMessage }
            : f
        )
      );
    }
  };

  const uploadAll = async () => {
    const pending = files.filter((f) => f.status === "pending");
    for (const file of pending) {
      await uploadFile(file);
    }
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const clearCompleted = () => {
    setFiles((prev) => prev.filter((f) => f.status !== "completed"));
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files);
    }
  };

  const completedCount = files.filter((f) => f.status === "completed").length;
  const pendingCount = files.filter((f) => f.status === "pending").length;

  return (
    <div className="animate-fade-in">
      {/* Page Header */}
      <div style={{ marginBottom: "32px" }}>
        <h1
          style={{ fontSize: "28px", fontWeight: "800", marginBottom: "8px" }}
          className="gradient-text"
        >
          Upload Documents
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "15px" }}>
          Upload PDF files for text extraction, OCR processing, and indexing
        </p>
      </div>

      {/* Dropzone */}
      <div
        className={cn("dropzone", isDragging && "active")}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          marginBottom: "32px",
          background: isDragging ? "rgba(124, 58, 237, 0.08)" : "var(--bg-secondary)",
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          style={{ display: "none" }}
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />
        <div
          style={{
            width: "72px",
            height: "72px",
            margin: "0 auto 20px",
            borderRadius: "20px",
            background: "var(--accent-gradient)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: isDragging ? 1 : 0.7,
            transition: "all 0.3s",
            transform: isDragging ? "scale(1.1)" : "scale(1)",
          }}
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
        </div>
        <p style={{ fontSize: "16px", fontWeight: "600", marginBottom: "8px" }}>
          {isDragging ? "Drop your PDFs here" : "Drag & drop PDF files here"}
        </p>
        <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>
          or click to browse • Max 200MB per file • PDF only
        </p>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="glass-card" style={{ padding: "24px" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "20px",
            }}
          >
            <h2 style={{ fontSize: "16px", fontWeight: "700" }}>
              Files ({files.length})
              {completedCount > 0 && (
                <span style={{ color: "var(--success)", fontWeight: "500", fontSize: "13px", marginLeft: "8px" }}>
                  ✓ {completedCount} completed
                </span>
              )}
            </h2>
            <div style={{ display: "flex", gap: "8px" }}>
              {completedCount > 0 && (
                <button className="btn-secondary" onClick={clearCompleted} style={{ padding: "6px 16px", fontSize: "13px" }}>
                  Clear Completed
                </button>
              )}
              {pendingCount > 0 && (
                <button className="btn-primary" onClick={uploadAll} style={{ padding: "6px 16px", fontSize: "13px" }}>
                  Upload All ({pendingCount})
                </button>
              )}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {files.map((file) => (
              <div
                key={file.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "16px",
                  padding: "16px",
                  borderRadius: "var(--radius-md)",
                  background: "var(--bg-tertiary)",
                  border: "1px solid var(--border-color)",
                }}
                className="animate-slide-in-up"
              >
                {/* PDF Icon */}
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "10px",
                    background: "rgba(239, 68, 68, 0.1)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <span style={{ fontSize: "11px", fontWeight: "800", color: "#ef4444" }}>PDF</span>
                </div>

                {/* File Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p
                    style={{
                      fontSize: "14px",
                      fontWeight: "500",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {file.file.name}
                  </p>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                    {formatFileSize(file.file.size)}
                    {file.error && (
                      <span style={{ color: "var(--error)", marginLeft: "8px" }}>
                        • {file.error}
                      </span>
                    )}
                  </p>

                  {/* Progress Bar */}
                  {(file.status === "uploading" || file.status === "processing") && (
                    <div className="progress-bar" style={{ marginTop: "8px" }}>
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  )}
                </div>

                {/* Status */}
                <span
                  className={`badge ${
                    file.status === "completed"
                      ? "badge-success"
                      : file.status === "uploading" || file.status === "processing"
                      ? "badge-warning"
                      : file.status === "failed"
                      ? "badge-error"
                      : "badge-info"
                  }`}
                >
                  {file.status === "uploading"
                    ? `${file.progress}%`
                    : file.status}
                </span>

                {/* Actions */}
                {(file.status === "pending" || file.status === "failed") && (
                  <button
                    onClick={() => removeFile(file.id)}
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "8px",
                      border: "none",
                      background: "rgba(239, 68, 68, 0.1)",
                      color: "var(--error)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "14px",
                    }}
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
