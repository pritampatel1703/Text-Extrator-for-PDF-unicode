import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Create Account — PDF Search Platform",
  description: "Create a new account for the PDF Search Platform.",
};

export default function RegisterLayout({ children }: { children: React.ReactNode }) {
  // Register page has its own full-screen layout (no sidebar/header)
  return <>{children}</>;
}
