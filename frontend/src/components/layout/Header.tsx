"use client";

import { useRouter, usePathname } from "next/navigation";
import { useState } from "react";

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  // Hide header on auth pages
  if (pathname === "/login" || pathname === "/register") {
    return null;
  }

  return (
    <header
      style={{
        position: "fixed",
        top: 0,
        left: "var(--sidebar-width)",
        right: 0,
        height: "var(--header-height)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 32px",
        borderBottom: "1px solid var(--border-color)",
        background: "rgba(10, 10, 15, 0.85)",
        backdropFilter: "blur(20px)",
        zIndex: 30,
      }}
    >
      {/* Global Search */}
      <form
        onSubmit={handleSearch}
        style={{
          flex: 1,
          maxWidth: "560px",
          position: "relative",
        }}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--text-muted)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{
            position: "absolute",
            left: "14px",
            top: "50%",
            transform: "translateY(-50%)",
            pointerEvents: "none",
          }}
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          id="global-search-input"
          type="text"
          placeholder="Search across all documents..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input"
          style={{
            paddingLeft: "42px",
            paddingRight: "80px",
            background: "var(--bg-secondary)",
            borderRadius: "var(--radius-lg)",
            height: "40px",
          }}
        />
        <kbd
          style={{
            position: "absolute",
            right: "12px",
            top: "50%",
            transform: "translateY(-50%)",
            fontSize: "11px",
            fontFamily: "inherit",
            color: "var(--text-muted)",
            background: "var(--bg-tertiary)",
            padding: "2px 8px",
            borderRadius: "4px",
            border: "1px solid var(--border-color)",
          }}
        >
          ⌘K
        </kbd>
      </form>

      {/* Right section */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {/* Notifications */}
        <button
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-color)",
            background: "transparent",
            color: "var(--text-secondary)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = "var(--accent-primary)";
            e.currentTarget.style.color = "var(--text-primary)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = "var(--border-color)";
            e.currentTarget.style.color = "var(--text-secondary)";
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </button>

        {/* User Avatar */}
        <div
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "50%",
            background: "var(--accent-gradient)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "14px",
            fontWeight: "700",
            color: "white",
            cursor: "pointer",
          }}
        >
          A
        </div>
      </div>
    </header>
  );
}
