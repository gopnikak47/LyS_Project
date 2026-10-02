"use client";

import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { RotateCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/feedback/states";

/** Ranh giới lỗi toàn cục: không hiển thị chi tiết kỹ thuật cho người dùng. */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations();

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main id="main" className="grid min-h-[60dvh] place-items-center px-4">
      <ErrorState
        title={t("states.errorTitle")}
        description={t("states.errorDescription")}
        className="w-full max-w-md"
        action={
          <Button variant="outline" onClick={reset}>
            <RotateCw aria-hidden />
            {t("common.retry")}
          </Button>
        }
      />
    </main>
  );
}
