import { useTranslations } from "next-intl";
import { Pin } from "lucide-react";
import { SentimentBadge, UrgentBadge } from "@/components/feedback/sentiment-badge";
import { StarRating } from "@/components/feedback/star-rating";
import { TopicChip } from "@/components/feedback/topic-chip";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { DemoResponse } from "@/lib/demo-data";
import { cn } from "@/lib/utils";

/** Bảng phản hồi mẫu (bản đầy đủ có lọc/phân trang server ở Giai đoạn 8 — FR-18). */
export function ResponsesTableDemo({ rows }: { rows: DemoResponse[] }) {
  const t = useTranslations("uiKit");
  // Phản hồi khẩn cấp luôn được ghim lên đầu danh sách.
  const sorted = [...rows].sort((a, b) => Number(!!b.urgent) - Number(!!a.urgent));

  return (
    <div className="overflow-hidden rounded-xl border bg-card shadow-soft">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow>
            <TableHead className="min-w-[18rem]">{t("columns.content")}</TableHead>
            <TableHead>{t("columns.rating")}</TableHead>
            <TableHead>{t("columns.sentiment")}</TableHead>
            <TableHead>{t("columns.topics")}</TableHead>
            <TableHead>{t("columns.source")}</TableHead>
            <TableHead className="text-right">{t("columns.time")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((row) => (
            <TableRow
              key={row.id}
              data-urgent={row.urgent || undefined}
              className={cn(
                row.urgent &&
                  "bg-urgent-soft/40 shadow-[inset_3px_0_0_var(--urgent)] hover:bg-urgent-soft/60",
              )}
            >
              <TableCell className="whitespace-normal">
                <div className="flex flex-col gap-1.5">
                  {row.urgent && (
                    <span className="flex items-center gap-2">
                      <UrgentBadge />
                      <Pin className="size-3.5 text-urgent-ink" aria-label={t("pinnedUrgent")} />
                    </span>
                  )}
                  <span>{row.content}</span>
                </div>
              </TableCell>
              <TableCell>
                <StarRating value={row.rating} />
              </TableCell>
              <TableCell>
                <SentimentBadge sentiment={row.sentiment} confidence={row.confidence} />
              </TableCell>
              <TableCell>
                <div className="flex flex-wrap gap-1">
                  {row.topics.map((topic) => (
                    <TopicChip key={topic.label} label={topic.label} color={topic.color} />
                  ))}
                </div>
              </TableCell>
              <TableCell className="text-muted-foreground">{row.source}</TableCell>
              <TableCell className="text-right text-muted-foreground tabular-nums">
                {row.time}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export function TableSkeleton({ rows = 4, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div className="overflow-hidden rounded-xl border bg-card" aria-hidden>
      <div className="flex gap-4 border-b bg-muted/50 px-4 py-3">
        {Array.from({ length: columns }, (_, i) => (
          <Skeleton key={i} className="h-4 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex gap-4 border-b px-4 py-4 last:border-0">
          {Array.from({ length: columns }, (_, c) => (
            <Skeleton key={c} className={cn("h-4 flex-1", c === 0 && "flex-[3]")} />
          ))}
        </div>
      ))}
    </div>
  );
}
