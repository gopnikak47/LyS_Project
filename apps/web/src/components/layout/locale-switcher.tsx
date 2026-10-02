"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Languages } from "lucide-react";
import { LOCALES } from "@lys/shared";
import { setLocale } from "@/i18n/actions";
import { cn } from "@/lib/utils";

export function LocaleSwitcher({ className }: { className?: string }) {
  const t = useTranslations("common");
  const current = useLocale();
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <label
      className={cn("inline-flex items-center gap-2 text-sm text-muted-foreground", className)}
    >
      <Languages className="size-4" aria-hidden />
      <span className="sr-only">{t("language")}</span>
      <select
        value={current}
        disabled={pending}
        onChange={(event) => {
          const next = event.target.value;
          startTransition(async () => {
            await setLocale(next);
            router.refresh();
          });
        }}
        className="h-8 rounded-md border border-input bg-background px-2 text-sm text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        {LOCALES.map((locale) => (
          <option key={locale} value={locale}>
            {t(`languages.${locale}`)}
          </option>
        ))}
      </select>
    </label>
  );
}
