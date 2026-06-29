import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import Header from "@/components/layout/Header";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: "PDF Search Platform — Enterprise Document Intelligence",
  description:
    "Upload, extract, and search across millions of PDF documents with AI-powered multilingual text extraction and ultra-fast global search.",
  keywords: "PDF, OCR, search, text extraction, multilingual, enterprise",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-mesh">
        <AuthProvider>
          <div style={{ display: "flex", minHeight: "100vh" }}>
            <Sidebar />
            <div
              style={{
                flex: 1,
                marginLeft: "var(--sidebar-width)",
                display: "flex",
                flexDirection: "column",
              }}
            >
              <Header />
              <main
                style={{
                  flex: 1,
                  padding: "24px 32px",
                  marginTop: "var(--header-height)",
                  maxWidth: "1400px",
                  width: "100%",
                  marginInline: "auto",
                }}
              >
                {children}
              </main>
            </div>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}

