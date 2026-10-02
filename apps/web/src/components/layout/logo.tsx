import Link from "next/link";
import { APP_INITIALS, APP_NAME } from "@/lib/config";
import { cn } from "@/lib/utils";

/** Logo placeholder: thay bằng logo thật bằng cách sửa component này hoặc biến APP_NAME. */
export function Logo({ href = "/", className }: { href?: string; className?: string }) {
  return (
    <Link
      href={href}
      aria-label={APP_NAME}
      className={cn(
        "inline-flex items-center gap-2 rounded-lg font-semibold tracking-tight focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none",
        className,
      )}
    >
      <span
        aria-hidden
        className="grid size-8 place-items-center rounded-lg bg-primary text-sm font-bold text-primary-foreground shadow-soft"
      >
        {APP_INITIALS}
      </span>
      <span className="text-base">{APP_NAME}</span>
    </Link>
  );
}
