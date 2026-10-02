"use client";

import {
  CircleCheckIcon,
  InfoIcon,
  Loader2Icon,
  OctagonXIcon,
  TriangleAlertIcon,
} from "lucide-react";
import { Toaster as Sonner, type ToasterProps } from "sonner";

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="system"
      position="top-center"
      richColors
      className="toaster group"
      icons={{
        success: <CircleCheckIcon className="size-4" />,
        info: <InfoIcon className="size-4" />,
        warning: <TriangleAlertIcon className="size-4" />,
        error: <OctagonXIcon className="size-4" />,
        loading: <Loader2Icon className="size-4 animate-spin" />,
      }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
          // Màu ngữ nghĩa của hệ thống (đạt tương phản AA) thay cho màu mặc định của sonner.
          "--success-bg": "var(--positive-soft)",
          "--success-text": "var(--positive-ink)",
          "--success-border": "color-mix(in oklch, var(--positive) 30%, transparent)",
          "--error-bg": "var(--negative-soft)",
          "--error-text": "var(--negative-ink)",
          "--error-border": "color-mix(in oklch, var(--negative) 30%, transparent)",
          "--warning-bg": "var(--urgent-soft)",
          "--warning-text": "var(--urgent-ink)",
          "--warning-border": "color-mix(in oklch, var(--urgent) 40%, transparent)",
          "--info-bg": "var(--primary-soft)",
          "--info-text": "var(--primary)",
          "--info-border": "color-mix(in oklch, var(--primary) 30%, transparent)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
