import { getTranslations } from "next-intl/server";
import { MessageSquareText, Smile, Star, TriangleAlert } from "lucide-react";
import { Card } from "@/components/ui/card";
import { SentimentBadge, UrgentBadge } from "@/components/feedback/sentiment-badge";

// Chiều cao cột minh họa (không phải số liệu thật).
const BARS = [42, 55, 48, 63, 58, 72, 68, 80];

/** Minh họa bảng điều khiển dựng bằng HTML/CSS (không dùng ảnh chụp sản phẩm khác). */
export async function HeroPreview() {
  const t = await getTranslations("marketing.preview");
  const stats = [
    {
      icon: MessageSquareText,
      label: t("responses"),
      value: "2.4k",
      tone: "bg-primary-soft text-primary",
    },
    {
      icon: Star,
      label: t("csat"),
      value: "4.4",
      tone: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
    },
    {
      icon: Smile,
      label: t("positiveRate"),
      value: "71%",
      tone: "bg-positive-soft text-positive-ink",
    },
    { icon: TriangleAlert, label: t("urgent"), value: "3", tone: "bg-urgent-soft text-urgent-ink" },
  ];

  return (
    <div role="img" aria-label={t("label")} className="relative">
      <div
        aria-hidden
        className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-tr from-primary/15 via-sky-200/30 to-transparent blur-2xl dark:via-sky-900/20"
      />
      <Card className="gap-4 overflow-hidden p-4 sm:p-5" aria-hidden>
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {stats.map(({ icon: Icon, label, value, tone }) => (
            <div key={label} className="rounded-lg border bg-background p-3">
              <span className={`mb-2 grid size-7 place-items-center rounded-md ${tone}`}>
                <Icon className="size-3.5" />
              </span>
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-lg font-semibold tabular-nums">{value}</p>
            </div>
          ))}
        </div>
        <div className="rounded-lg border bg-background p-3">
          <p className="mb-3 text-xs font-medium text-muted-foreground">{t("trend")}</p>
          <div className="flex h-24 items-end gap-2">
            {BARS.map((h, i) => (
              <div
                key={i}
                className="flex flex-1 flex-col justify-end gap-0.5"
                style={{ height: "100%" }}
              >
                <div
                  className="rounded-t-sm bg-negative/70"
                  style={{ height: `${(100 - h) * 0.35}%` }}
                />
                <div className="rounded-b-sm bg-positive/80" style={{ height: `${h}%` }} />
              </div>
            ))}
          </div>
        </div>
        <ul className="space-y-2">
          <li className="flex items-start justify-between gap-3 rounded-lg border border-urgent/40 bg-urgent-soft/50 p-3">
            <p className="text-sm">{t("sample3")}</p>
            <UrgentBadge />
          </li>
          <li className="flex items-start justify-between gap-3 rounded-lg border bg-background p-3">
            <p className="text-sm">{t("sample1")}</p>
            <SentimentBadge sentiment="positive" />
          </li>
          <li className="hidden items-start justify-between gap-3 rounded-lg border bg-background p-3 sm:flex">
            <p className="text-sm">{t("sample2")}</p>
            <SentimentBadge sentiment="neutral" />
          </li>
        </ul>
      </Card>
    </div>
  );
}
