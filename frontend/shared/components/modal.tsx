"use client";

import type { ReactNode } from "react";
import { X } from "lucide-react";
import { Button } from "@/shared/components/button";
import { Card } from "@/shared/components/card";

type ModalProps = {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
};

export function Modal({
  open,
  title,
  description,
  onClose,
  children
}: ModalProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[color:rgba(15,23,42,0.45)] p-4">
      <Card className="w-full max-w-2xl p-0">
        <div className="flex items-start justify-between border-b border-[var(--line)] px-6 py-5">
          <div>
            <h2 className="text-xl font-semibold">{title}</h2>
            {description ? (
              <p className="mt-2 text-sm text-[var(--ink-soft)]">{description}</p>
            ) : null}
          </div>
          <Button
            aria-label="Close modal"
            className="h-10 w-10 justify-center px-0"
            variant="ghost"
            onClick={onClose}
          >
            <X size={16} />
          </Button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </Card>
    </div>
  );
}
