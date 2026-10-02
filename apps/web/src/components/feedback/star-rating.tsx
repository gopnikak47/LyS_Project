import { useTranslations } from "next-intl";
import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

/** Hiển thị số sao (chỉ đọc). Bản tương tác cho trang khách làm ở Giai đoạn 5. */
export function StarRating({
  value,
  max = 5,
  className,
}: {
  value: number;
  max?: number;
  className?: string;
}) {
  const t = useTranslations("uiKit");
  return (
    <span
      className={cn("inline-flex items-center gap-0.5", className)}
      role="img"
      aria-label={t("ratingLabel", { value })}
    >
      {Array.from({ length: max }, (_, i) => (
        <Star
          key={i}
          aria-hidden
          className={cn(
            "size-3.5",
            i < value
              ? "fill-amber-400 text-amber-400"
              : "fill-transparent text-muted-foreground/40",
          )}
        />
      ))}
    </span>
  );
}
