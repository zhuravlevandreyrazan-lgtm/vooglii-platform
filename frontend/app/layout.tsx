import type { Metadata } from "next";
import Script from "next/script";
import type { ReactNode } from "react";
import { PlatformShell } from "@/shared/layout";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "VOOGLII Platform",
  description: "Платформа для управления бизнесом, финансами, рекламой и аналитикой Wildberries.",
  icons: {
    icon: [
      { url: "/brand/favicon.svg", type: "image/svg+xml" },
      { url: "/brand/logo-icon.svg", type: "image/svg+xml" }
    ],
    shortcut: "/brand/favicon.svg",
    apple: "/brand/apple-touch-icon.svg"
  }
};

export default function RootLayout({
  children
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="ru">
      <body>
        <Script src="/runtime-config.js" strategy="beforeInteractive" />
        <PlatformShell>{children}</PlatformShell>
      </body>
    </html>
  );
}
