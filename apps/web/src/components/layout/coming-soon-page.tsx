import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { ComingSoonState } from "@/components/feedback/states";
import { PageHeader } from "./page-header";

/** Trang khung cho màn hình chưa xây dựng: ghi rõ giai đoạn sẽ hoàn thiện. */
export async function ComingSoonPage({ title, stage }: { title: string; stage: number }) {
  const t = await getTranslations();
  return (
    <div className="space-y-6">
      <PageHeader title={title} />
      <ComingSoonState
        title={t("states.comingSoonTitle")}
        description={t("states.comingSoonDescription", { stage })}
        action={
          <Button variant="outline" asChild>
            <Link href="/surveys">{t("app.nav.mySurveys")}</Link>
          </Button>
        }
      />
    </div>
  );
}
