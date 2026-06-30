import type { HTMLAttributes, ReactNode } from "react";
import type { StatusTone } from "@/types/platform";

export type WidgetStatus = "loading" | "error" | "empty" | "success";

export type WidgetState = {
  status: WidgetStatus;
  title?: string;
  message?: string;
};

export type WidgetAction = {
  label: string;
  onClick?: () => void;
  href?: string;
  disabled?: boolean;
  icon?: ReactNode;
};

export type WidgetCardProps = HTMLAttributes<HTMLDivElement> & {
  title: string;
  subtitle?: string;
  status?:
    | ReactNode
    | {
        label: string;
        tone: StatusTone;
      };
  children?: ReactNode;
  actions?: ReactNode;
  updatedAt?: string;
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
  emptyMessage?: string;
  className?: string;
};
