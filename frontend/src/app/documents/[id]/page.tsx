"use client";

import { useEffect, useState, useRef, useCallback, use, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api, type DocumentDetail, type PageDetail, type TextBlock } from "@/lib/api";
import { formatFileSize, formatDate, getLanguageName } from "@/lib/utils";

export default function DocumentViewerPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const searchParams = useSearchParams();
  const highlightQuery = searchParams.get("highlight") || "";
  const initialPage = parseInt(searchParams.get("page") || "1", 10);

  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageDetail, setPageDetail] = useState<PageDetail | null>(null);
  const [zoom, setZoom] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showTextBlocks, setShowTextBlocks] = useState(false);
  const [searchInDoc, setSearchInDoc] = useState(highlightQuery);
  const [searchMatches, setSearchMatches] = useState<Array<{ page: number; text: string }>>([]);
  const [sidebarTab, setSidebarTab] = useState<"info" | "text" | "search">("info");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderTaskRef = useRef<any>(null);

  // Load document
  useEffect(() => {
    loadDocument();
  }, [id]);

  // Load page detail when page changes
  useEffect(() => {
    if (document) {
      loadPageDetail(currentPage);
    }
  }, [currentPage, document]);

  async function loadDocument() {
    setLoading(true);
    try {
      const doc = await api.getDocument(id);
      setDocument(doc);
    } catch (e) {
      console.error("Failed to load document:", e);
    } finally {
      setLoading(false);
    }
  }

  async function loadPageDetail(pageNum: number) {
    try {
      const page = await api.getPage(id, pageNum);
      setPageDetail(page);
    } catch (e) {
      console.error("Failed to load page:", e);
    }
  }

  // Render PDF page on canvas using pdf.js
  useEffect(() => {
    if (!document || !canvasRef.current) return;
    let isMounted = true;

    async function renderPage() {
      try {
        const pdfjs = await import("pdfjs-dist");
        pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

        // Get document file URL — derive backend base from API URL
        const fileData = await api.getDocumentFile(id);
        const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
        const backendBase = apiBase.replace(/\/api\/v1\/?$/, "");
        // If file_path is a full URL (cloud S3), use it directly; otherwise prepend backend base
        const pdfUrl = fileData.file_path.startsWith("http") ? fileData.file_path : `${backendBase}${fileData.file_path}`;

        const loadingTask = pdfjs.getDocument({ url: pdfUrl });
        const pdf = await loadingTask.promise;
        if (!isMounted) return;

        const page = await pdf.getPage(currentPage);
        if (!isMounted) return;

        const canvas = canvasRef.current;
        if (!canvas) return;

        const context = canvas.getContext("2d");
        if (!context) return;

        const viewport = page.getViewport({ scale: zoom * 1.5 });
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        if (renderTaskRef.current) {
          try {
            renderTaskRef.current.cancel();
          } catch (e) {}
        }

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
          canvas: canvas,
        };
        const renderTask = page.render(renderContext as any);
        renderTaskRef.current = renderTask;
        
        await renderTask.promise;
      } catch (e: any) {
        if (e.name !== "RenderingCancelledException") {
          console.error("PDF render error:", e);
        }
      }
    }

    renderPage();
    return () => {
      isMounted = false;
      if (renderTaskRef.current) {
        try {
          renderTaskRef.current.cancel();
        } catch (e) {}
      }
    };
  }, [document, currentPage, zoom, id]);

  // Search within document pages
  const searchInDocument = useCallback(() => {
    if (!document || !searchInDoc.trim()) {
      setSearchMatches([]);
      return;
    }

    const matches: Array<{ page: number; text: string }> = [];
    const query = searchInDoc.toLowerCase();

    document.pages.forEach((page) => {
      if (page.extracted_text?.toLowerCase().includes(query)) {
        const idx = page.extracted_text.toLowerCase().indexOf(query);
        const start = Math.max(0, idx - 50);
        const end = Math.min(page.extracted_text.length, idx + query.length + 50);
        matches.push({
          page: page.page_number,
          text: "..." + page.extracted_text.slice(start, end) + "...",
        });
      }
    });

    setSearchMatches(matches);
  }, [document, searchInDoc]);

  useEffect(() => {
    searchInDocument();
  }, [searchInDoc, searchInDocument]);

  if (loading) {
    return (
      <div className="animate-fade-in" style={{ display: "flex", gap: "24px" }}>
        <div className="skeleton" style={{ flex: 1, height: "80vh", borderRadius: "var(--radius-lg)" }} />
        <div className="skeleton" style={{ width: "320px", height: "80vh", borderRadius: "var(--radius-lg)" }} />
      </div>
    );
  }

  if (!document) {
    return (
      <div style={{ textAlign: "center", padding: "60px", color: "var(--text-muted)" }}>
        <p style={{ fontSize: "48px", marginBottom: "16px" }}>📄</p>
        <p>Document not found</p>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Document Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "20px",
        }}
      >
        <div>
          <h1 style={{ fontSize: "20px", fontWeight: "700", marginBottom: "4px" }}>
            {document.original_filename}
          </h1>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            {document.page_count} pages • {formatFileSize(document.file_size)} • {getLanguageName(document.primary_language)}
          </p>
        </div>
      </div>

      {/* Viewer Layout */}
      <div style={{ display: "flex", gap: "20px", height: "calc(100vh - 200px)" }}>
        {/* PDF Canvas */}
        <div
          className="glass-card"
          style={{
            flex: 1,
            overflow: "auto",
            position: "relative",
            padding: "16px",
          }}
        >
          {/* Toolbar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "16px",
              padding: "8px 16px",
              background: "var(--bg-tertiary)",
              borderRadius: "var(--radius-md)",
            }}
          >
            {/* Page Navigation */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <button
                className="btn-secondary"
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage <= 1}
                style={{ padding: "6px 12px", fontSize: "13px", opacity: currentPage <= 1 ? 0.5 : 1 }}
              >
                ←
              </button>
              <span style={{ fontSize: "13px", color: "var(--text-secondary)", minWidth: "100px", textAlign: "center" }}>
                Page{" "}
                <input
                  type="number"
                  value={currentPage}
                  onChange={(e) => {
                    const p = parseInt(e.target.value);
                    if (p >= 1 && p <= document.page_count) setCurrentPage(p);
                  }}
                  style={{
                    width: "50px",
                    textAlign: "center",
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "6px",
                    padding: "2px 4px",
                    color: "var(--text-primary)",
                    fontSize: "13px",
                  }}
                />{" "}
                of {document.page_count}
              </span>
              <button
                className="btn-secondary"
                onClick={() => setCurrentPage(Math.min(document.page_count, currentPage + 1))}
                disabled={currentPage >= document.page_count}
                style={{ padding: "6px 12px", fontSize: "13px", opacity: currentPage >= document.page_count ? 0.5 : 1 }}
              >
                →
              </button>
            </div>

            {/* Zoom Controls */}
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <button className="btn-secondary" onClick={() => setZoom(Math.max(0.5, zoom - 0.25))} style={{ padding: "6px 10px", fontSize: "13px" }}>
                −
              </button>
              <span style={{ fontSize: "13px", color: "var(--text-secondary)", minWidth: "50px", textAlign: "center" }}>
                {Math.round(zoom * 100)}%
              </span>
              <button className="btn-secondary" onClick={() => setZoom(Math.min(3, zoom + 0.25))} style={{ padding: "6px 10px", fontSize: "13px" }}>
                +
              </button>
              <button
                className="btn-secondary"
                onClick={() => setShowTextBlocks(!showTextBlocks)}
                style={{
                  padding: "6px 12px",
                  fontSize: "13px",
                  background: showTextBlocks ? "rgba(124, 58, 237, 0.12)" : undefined,
                  borderColor: showTextBlocks ? "var(--accent-primary)" : undefined,
                }}
              >
                {showTextBlocks ? "Hide" : "Show"} Blocks
              </button>
            </div>
          </div>

          {/* Canvas with Text Block Overlays */}
          <div style={{ position: "relative", display: "inline-block" }}>
            <canvas ref={canvasRef} style={{ maxWidth: "100%", borderRadius: "8px" }} />

            {/* Text block overlays */}
            {showTextBlocks &&
              pageDetail?.text_blocks.map((block) => (
                <div
                  key={block.id}
                  className="pdf-text-highlight"
                  title={block.text_content}
                  style={{
                    left: `${(block.x / (pageDetail.page_width || 612)) * 100}%`,
                    top: `${(block.y / (pageDetail.page_height || 792)) * 100}%`,
                    width: `${(block.width / (pageDetail.page_width || 612)) * 100}%`,
                    height: `${(block.height / (pageDetail.page_height || 792)) * 100}%`,
                  }}
                />
              ))}
          </div>
        </div>

        {/* Sidebar */}
        <div
          className="glass-card"
          style={{
            width: "340px",
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Tabs */}
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid var(--border-color)",
            }}
          >
            {(["info", "text", "search"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setSidebarTab(tab)}
                style={{
                  flex: 1,
                  padding: "12px",
                  background: "transparent",
                  border: "none",
                  borderBottom: sidebarTab === tab ? "2px solid var(--accent-primary)" : "2px solid transparent",
                  color: sidebarTab === tab ? "var(--text-primary)" : "var(--text-muted)",
                  fontSize: "13px",
                  fontWeight: "600",
                  cursor: "pointer",
                  textTransform: "capitalize",
                }}
              >
                {tab === "info" ? "📋 Info" : tab === "text" ? "📝 Text" : "🔍 Search"}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div style={{ flex: 1, overflow: "auto", padding: "16px" }}>
            {/* Info Tab */}
            {sidebarTab === "info" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                <InfoRow label="Filename" value={document.original_filename} />
                <InfoRow label="Pages" value={String(document.page_count)} />
                <InfoRow label="Size" value={formatFileSize(document.file_size)} />
                <InfoRow label="Language" value={getLanguageName(document.primary_language)} />
                <InfoRow label="Author" value={document.author || "—"} />
                <InfoRow label="Title" value={document.title || "—"} />
                <InfoRow label="Status" value={document.processing_status} />
                <InfoRow label="Uploaded" value={formatDate(document.upload_date)} />
                <InfoRow label="Created" value={formatDate(document.creation_date)} />
                {pageDetail && (
                  <>
                    <hr style={{ border: "none", borderTop: "1px solid var(--border-color)" }} />
                    <InfoRow label="Current Page" value={String(currentPage)} />
                    <InfoRow label="Words" value={String(pageDetail.word_count)} />
                    <InfoRow label="Page Lang" value={getLanguageName(pageDetail.language)} />
                    <InfoRow label="Text Layer" value={pageDetail.has_text_layer ? "Yes" : "No"} />
                    <InfoRow label="OCR Applied" value={pageDetail.ocr_applied ? "Yes" : "No"} />
                    <InfoRow label="Text Blocks" value={String(pageDetail.text_blocks.length)} />
                  </>
                )}
              </div>
            )}

            {/* Text Tab */}
            {sidebarTab === "text" && (
              <div>
                <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "12px" }}>
                  Extracted text for page {currentPage}:
                </p>
                <div
                  style={{
                    background: "var(--bg-tertiary)",
                    borderRadius: "var(--radius-md)",
                    padding: "16px",
                    fontSize: "13px",
                    lineHeight: "1.7",
                    color: "var(--text-secondary)",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    maxHeight: "calc(100vh - 400px)",
                    overflow: "auto",
                  }}
                >
                  {pageDetail?.extracted_text || "No text extracted for this page."}
                </div>
              </div>
            )}

            {/* Search Tab */}
            {sidebarTab === "search" && (
              <div>
                <input
                  type="text"
                  placeholder="Search within document..."
                  value={searchInDoc}
                  onChange={(e) => setSearchInDoc(e.target.value)}
                  className="input"
                  style={{ marginBottom: "16px" }}
                />

                {searchMatches.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      {searchMatches.length} matches found
                    </p>
                    {searchMatches.map((match, i) => (
                      <button
                        key={i}
                        onClick={() => setCurrentPage(match.page)}
                        style={{
                          textAlign: "left",
                          padding: "10px 12px",
                          borderRadius: "var(--radius-sm)",
                          background: match.page === currentPage ? "rgba(124, 58, 237, 0.12)" : "var(--bg-tertiary)",
                          border: match.page === currentPage ? "1px solid var(--accent-primary)" : "1px solid var(--border-color)",
                          cursor: "pointer",
                          color: "var(--text-secondary)",
                          fontSize: "12px",
                          lineHeight: "1.5",
                        }}
                      >
                        <span style={{ fontWeight: "600", color: "var(--text-primary)", display: "block", marginBottom: "4px" }}>
                          Page {match.page}
                        </span>
                        {match.text}
                      </button>
                    ))}
                  </div>
                ) : searchInDoc ? (
                  <p style={{ fontSize: "13px", color: "var(--text-muted)", textAlign: "center", padding: "20px" }}>
                    No matches found
                  </p>
                ) : null}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
      <span style={{ fontSize: "12px", color: "var(--text-muted)", flexShrink: 0 }}>{label}</span>
      <span
        style={{
          fontSize: "13px",
          color: "var(--text-primary)",
          fontWeight: "500",
          textAlign: "right",
          maxWidth: "200px",
          wordBreak: "break-all",
        }}
      >
        {value}
      </span>
    </div>
  );
}
