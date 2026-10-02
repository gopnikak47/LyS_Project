import { cn } from "@/lib/utils";

/** Chip chủ đề; màu lấy từ cấu hình chủ đề của workspace (FR-12). */
export function TopicChip({
  label,
  color = "var(--primary)",
  className,
}: {
  label: string;
  color?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border bg-background px-2 py-0.5 text-xs font-medium whitespace-nowrap text-foreground",
        className,
      )}
    >
      <span aria-hidden className="size-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}
