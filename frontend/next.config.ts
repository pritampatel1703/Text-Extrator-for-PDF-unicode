import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  // Exclude pdfjs-dist worker from server-side bundling
  serverExternalPackages: ["pdfjs-dist"],

  // Next.js 16 uses Turbopack by default
  turbopack: {
    resolveAlias: {
      // pdfjs-dist optional dependency — not needed in browser
      canvas: { browser: "./empty-module.js" },
    },
  },
};

export default nextConfig;

