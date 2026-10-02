import { useTranslations } from "next-intl";
import { CircleAlert, Frown, Meh, Smile } from "lucide-react";
import type { Sentiment } from "@lys/shared";
import { Badge } from "@/components/ui/badge";

const ICONS = { positive: Smile, negative: Frown, neutral: Meh } as const;

/**
 * Nhãn cảm xúc với màu ngữ nghĩa cố định (Xanh/Đỏ/Xám).
 * Luôn kèm biểu tượng + chữ để không phụ thuộc vào màu (hỗ trợ người mù màu).
 */
export function SentimentBadge({
  sentiment,
  confidence,
}: {
  sentiment: Sentiment;
  /** Độ tin cậy 0–1 của mô hình (tùy chọn). */
  confidence?: number;
}) {
  const t = useTranslations("sentiment");
  const Icon = ICONS[sentiment];
  return (
    <Badge variant={sentiment} data-sentiment={sentiment}>
      <Icon aria-hidden />
      {t(sentiment)}
      {confidence !== undefined && (
        <span
          className="font-normal opacity-80"
          title={t("confidence", { value: Math.round(confidence * 100) })}
        >
          · {Math.round(confidence * 100)}%
        </span>
      )}
    </Badge>
  );
}

export function UrgentBadge() {
  const t = useTranslations("sentiment");
  return (
    <Badge variant="urgent" className="font-semibold">
      <CircleAlert aria-hidden />
      {t("urgent")}
    </Badge>
  );
}
