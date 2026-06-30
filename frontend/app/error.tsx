"use client";

import { useEffect } from "react";
import { Button } from "@/shared/components/button";

export default function GlobalError({
  error,
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto max-w-3xl rounded-[32px] border border-[var(--line)] bg-white/80 p-10 shadow-[var(--shadow-soft)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--danger)]">500</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em]">Something went wrong</h1>
      <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
        The workspace encountered an unexpected error. Runtime diagnostics remain available through the backend health endpoints.
      </p>
      <div className="mt-6">
        <Button variant="secondary" onClick={reset}>
          Try again
        </Button>
      </div>
    </div>
  );
}
