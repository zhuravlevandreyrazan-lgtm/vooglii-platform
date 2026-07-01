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
      { url: "/brand/vooglii-logo-full.png", type: "image/png" }
    ],
    shortcut: "/brand/vooglii-logo-full.png",
    apple: "/brand/vooglii-logo-full.png"
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
