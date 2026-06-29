import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login — PDF Search Platform",
  description: "Sign in to your PDF Search Platform account.",
};

export default function LoginLayout({ children }: { children: React.ReactNode }) {
  // Login page has its own full-screen layout (no sidebar/header)
  return <>{children}</>;
}
