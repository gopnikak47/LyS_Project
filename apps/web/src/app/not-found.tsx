import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { SearchX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/feedback/states";

export default async function NotFound() {
  const t = await getTranslations("states");
  return (
    <main id="main" className="grid min-h-dvh place-items-center px-4">
      <EmptyState
        icon={SearchX}
        title={t("notFoundTitle")}
        description={t("notFoundDescription")}
        className="w-full max-w-md"
        action={
          <Button asChild>
            <Link href="/">{t("backHome")}</Link>
          </Button>
        }
      />
    </main>
  );
}
