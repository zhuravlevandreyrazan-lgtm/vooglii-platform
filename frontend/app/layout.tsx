import type { Metadata } from "next";
import Script from "next/script";
import type { ReactNode } from "react";
import { PlatformShell } from "@/shared/layout";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "VOOGLII Platform",
  description: "Commercial SaaS foundation for marketplace sellers."
};

export default function RootLayout({
  children
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <Script src="/runtime-config.js" strategy="beforeInteractive" />
        <PlatformShell>{children}</PlatformShell>
      </body>
    </html>
  );
}
