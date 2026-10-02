import type { LucideIcon } from "lucide-react";
import { TrendingDown, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

type Tone = "default" | "positive" | "negative" | "urgent";

const TONE_ICON: Record<Tone, string> = {
  default: "bg-primary-soft text-primary",
  positive: "bg-positive-soft text-positive-ink",
  negative: "bg-negative-soft text-negative-ink",
  urgent: "bg-urgent-soft text-urgent-ink",
};

export function KpiCard({
  label,
  value,
  icon: Icon,
  tone = "default",
  delta,
  deltaLabel,
  /** Tăng có phải là tốt không (ví dụ số cảnh báo khẩn tăng là xấu). */
  higherIsBetter = true,
}: {
  label: string;
  value: string;
  icon: LucideIcon;
  tone?: Tone;
  delta?: number;
  deltaLabel?: string;
  higherIsBetter?: boolean;
}) {
  const good = delta !== undefined && delta >= 0 === higherIsBetter;
  return (
    <Card className="gap-3 p-5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <span className={cn("grid size-9 place-items-center rounded-lg", TONE_ICON[tone])}>
          <Icon className="size-4.5" aria-hidden />
        </span>
      </div>
      <p className="text-3xl font-semibold tracking-tight tabular-nums">{value}</p>
      {delta !== undefined && (
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-medium",
              good ? "bg-positive-soft text-positive-ink" : "bg-negative-soft text-negative-ink",
            )}
          >
            {delta >= 0 ? (
              <TrendingUp className="size-3" aria-hidden />
            ) : (
              <TrendingDown className="size-3" aria-hidden />
            )}
            {delta >= 0 ? "+" : ""}
            {delta}%
          </span>
          {deltaLabel}
        </p>
      )}
    </Card>
  );
}

export function KpiCardSkeleton() {
  return (
    <Card className="gap-3 p-5" aria-hidden>
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="size-9 rounded-lg" />
      </div>
      <Skeleton className="h-8 w-20" />
      <Skeleton className="h-4 w-32" />
    </Card>
  );
}
