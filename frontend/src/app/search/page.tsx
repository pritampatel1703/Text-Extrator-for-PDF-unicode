"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api, type SearchResponse, type SearchHit } from "@/lib/api";
import { debounce, getLanguageName } from "@/lib/utils";

function SearchContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialQuery = searchParams.get("q") || "";

  const [query, setQuery] = useState(initialQuery);
  const [searchType, setSearchType] = useState("fulltext");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);

  // Fetch suggestions
  const fetchSuggestions = useCallback(
    debounce(async (q: string) => {
      if (q.length < 2) {
        setSuggestions([]);
        return;
      }
      try {
        const data = await api.getSuggestions(q);
        setSuggestions(data.suggestions || []);
      } catch {
        setSuggestions([]);
      }
    }, 300) as (...args: unknown[]) => void,
    []
  );

  // Execute search
  const executeSearch = useCallback(
    async (searchQuery: string, page: number = 1) => {
      if (!searchQuery.trim()) return;

      setLoading(true);
      setSuggestions([]);
      try {
        const data = await api.search({
          q: searchQuery,
          search_type: searchType,
          page,
          page_size: 20,
          fuzzy: true,
        });
        setResults(data);
        setCurrentPage(page);

        // Update URL
        const params = new URLSearchParams();
        params.set("q", searchQuery);
        if (searchType !== "fulltext") params.set("type", searchType);
        if (page > 1) params.set("page", String(page));
        router.replace(`/search?${params.toString()}`, { scroll: false });
      } catch (error) {
        console.error("Search error:", error);
      } finally {
        setLoading(false);
      }
    },
    [searchType, router]
  );

  // Auto-search on mount if query exists
  useEffect(() => {
    if (initialQuery) {
      executeSearch(initialQuery);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(query);
  };

  const searchTypes = [
    { value: "fulltext", label: "Full-Text", icon: "📝" },
    { value: "semantic", label: "Semantic", icon: "🧠" },
    { value: "hybrid", label: "Hybrid", icon: "⚡" },
  ];

  return (
    <div className="animate-fade-in">
      {/* Page Header */}
      <div style={{ marginBottom: "32px" }}>
        <h1
          style={{ fontSize: "28px", fontWeight: "800", marginBottom: "8px" }}
          className="gradient-text"
        >
          Global Search
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: "15px" }}>
          Search across all documents with full-text, semantic, or hybrid search
        </p>
      </div>

      {/* Search Bar */}
      <div style={{ marginBottom: "24px" }}>
        <form onSubmit={handleSubmit} style={{ position: "relative" }}>
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--text-muted)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              position: "absolute",
              left: "20px",
              top: "50%",
              transform: "translateY(-50%)",
              pointerEvents: "none",
            }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            id="search-input"
            type="text"
            placeholder='Search documents... Use "quotes" for exact phrases'
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              fetchSuggestions(e.target.value);
            }}
            className="input"
            style={{
              paddingLeft: "52px",
              fontSize: "16px",
              height: "56px",
              borderRadius: "var(--radius-xl)",
              background: "var(--bg-secondary)",
            }}
          />
          <button
            type="submit"
            className="btn-primary"
            style={{
              position: "absolute",
              right: "8px",
              top: "50%",
              transform: "translateY(-50%)",
              padding: "8px 24px",
              borderRadius: "var(--radius-lg)",
            }}
          >
            Search
          </button>
        </form>

        {/* Suggestions */}
        {suggestions.length > 0 && (
          <div
            className="glass-card"
            style={{
              marginTop: "8px",
              padding: "8px",
              position: "absolute",
              zIndex: 10,
              width: "calc(100% - 64px)",
              maxWidth: "1400px",
            }}
          >
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuery(s);
                  executeSearch(s);
                }}
                style={{
                  width: "100%",
                  textAlign: "left",
                  padding: "10px 16px",
                  background: "transparent",
                  border: "none",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "14px",
                  transition: "all 0.15s",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "rgba(124, 58, 237, 0.08)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "transparent";
                }}
                dangerouslySetInnerHTML={{ __html: s }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Search Type Toggle */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          marginBottom: "24px",
        }}
      >
        {searchTypes.map((type) => (
          <button
            key={type.value}
            onClick={() => setSearchType(type.value)}
            style={{
              padding: "8px 20px",
              borderRadius: "100px",
              border: "1px solid",
              borderColor:
                searchType === type.value
                  ? "var(--accent-primary)"
                  : "var(--border-color)",
              background:
                searchType === type.value
                  ? "rgba(124, 58, 237, 0.12)"
                  : "transparent",
              color:
                searchType === type.value
                  ? "var(--text-primary)"
                  : "var(--text-secondary)",
              fontSize: "13px",
              fontWeight: "500",
              cursor: "pointer",
              transition: "all 0.2s",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <span>{type.icon}</span>
            {type.label}
          </button>
        ))}
      </div>

      {/* Results */}
      {loading && (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="skeleton"
              style={{ height: "120px", borderRadius: "var(--radius-lg)" }}
            />
          ))}
        </div>
      )}

      {results && !loading && (
        <div>
          {/* Results Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "20px",
            }}
          >
            <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
              <span style={{ fontWeight: "600", color: "var(--text-primary)" }}>
                {results.total_hits.toLocaleString()}
              </span>{" "}
              results found in{" "}
              <span style={{ fontWeight: "600", color: "var(--accent-primary)" }}>
                {results.took_ms}ms
              </span>
            </p>
          </div>

          {/* Result Cards */}
          <div
            className="stagger-children"
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            {results.hits.map((hit, index) => (
              <SearchResultCard key={`${hit.document_id}-${hit.page_number}-${index}`} hit={hit} />
            ))}
          </div>

          {/* Pagination */}
          {results.total_pages > 1 && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                marginTop: "32px",
              }}
            >
              <button
                className="btn-secondary"
                disabled={currentPage <= 1}
                onClick={() => executeSearch(query, currentPage - 1)}
                style={{ padding: "8px 16px", fontSize: "13px", opacity: currentPage <= 1 ? 0.5 : 1 }}
              >
                ← Previous
              </button>
              <span
                style={{
                  padding: "8px 16px",
                  fontSize: "13px",
                  color: "var(--text-secondary)",
                }}
              >
                Page {currentPage} of {results.total_pages}
              </span>
              <button
                className="btn-secondary"
                disabled={currentPage >= results.total_pages}
                onClick={() => executeSearch(query, currentPage + 1)}
                style={{
                  padding: "8px 16px",
                  fontSize: "13px",
                  opacity: currentPage >= results.total_pages ? 0.5 : 1,
                }}
              >
                Next →
              </button>
            </div>
          )}

          {/* No Results */}
          {results.hits.length === 0 && (
            <div
              style={{
                textAlign: "center",
                padding: "60px 20px",
                color: "var(--text-muted)",
              }}
            >
              <p style={{ fontSize: "48px", marginBottom: "16px" }}>🔍</p>
              <p style={{ fontSize: "18px", fontWeight: "600", marginBottom: "8px", color: "var(--text-secondary)" }}>
                No results found
              </p>
              <p style={{ fontSize: "14px" }}>
                Try different keywords or use semantic search for concept-based matching
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SearchResultCard({ hit }: { hit: SearchHit }) {
  return (
    <Link
      href={`/documents/${hit.document_id}?page=${hit.page_number}&highlight=${encodeURIComponent(hit.content_snippet.slice(0, 50))}`}
      style={{ textDecoration: "none" }}
    >
      <div
        className="glass-card"
        style={{
          padding: "20px 24px",
          cursor: "pointer",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            marginBottom: "12px",
          }}
        >
          <div style={{ flex: 1 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                marginBottom: "6px",
              }}
            >
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: "800",
                  color: "#ef4444",
                  background: "rgba(239, 68, 68, 0.1)",
                  padding: "2px 6px",
                  borderRadius: "4px",
                }}
              >
                PDF
              </span>
              <span
                style={{
                  fontSize: "14px",
                  fontWeight: "600",
                  color: "var(--text-primary)",
                }}
              >
                {hit.filename}
              </span>
              <span
                style={{
                  fontSize: "12px",
                  color: "var(--text-muted)",
                }}
              >
                • Page {hit.page_number}
              </span>
            </div>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            {hit.language && (
              <span className="badge badge-info">
                {getLanguageName(hit.language)}
              </span>
            )}
            <span
              style={{
                fontSize: "12px",
                color: "var(--accent-primary)",
                fontWeight: "600",
              }}
            >
              {hit.score.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Highlighted Content */}
        <p
          style={{
            fontSize: "14px",
            lineHeight: "1.6",
            color: "var(--text-secondary)",
          }}
          dangerouslySetInnerHTML={{ __html: hit.highlighted_content }}
        />

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            marginTop: "12px",
            fontSize: "12px",
            color: "var(--text-muted)",
          }}
        >
          {hit.author && <span>Author: {hit.author}</span>}
          {hit.word_count > 0 && <span>{hit.word_count} words</span>}
          {hit.upload_date && (
            <span>Uploaded: {new Date(hit.upload_date).toLocaleDateString()}</span>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="skeleton" style={{ height: "400px", borderRadius: "var(--radius-lg)" }} />}>
      <SearchContent />
    </Suspense>
  );
}
