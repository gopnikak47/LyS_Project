import Link from "next/link";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Info, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader } from "@/components/layout/page-header";
import { SurveyCard } from "@/components/surveys/survey-card";
import { DEMO_SURVEYS } from "@/lib/demo-data";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("surveys");
  return { title: t("title") };
}

export default async function SurveysPage() {
  const t = await getTranslations("surveys");

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("title")}
        description={t("subtitle")}
        actions={
          <Button asChild>
            <Link href="/surveys/new">
              <Plus aria-hidden />
              {t("create")}
            </Link>
          </Button>
        }
      />

      <p
        role="note"
        className="flex items-start gap-2 rounded-lg border border-primary/20 bg-primary-soft px-3 py-2 text-sm text-primary"
      >
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
        {t("demoNotice")}
      </p>

      <div className="flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <span className="sr-only">{t("searchPlaceholder")}</span>
          <Search
            className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden
          />
          <Input type="search" placeholder={t("searchPlaceholder")} className="bg-card pl-9" />
        </label>
        <label className="sm:w-56">
          <span className="sr-only">{t("statusFilter")}</span>
          <select className="h-10 w-full rounded-lg border border-input bg-card px-3 text-sm focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none">
            <option value="">{t("allStatuses")}</option>
            <option value="draft">{t("status.draft")}</option>
            <option value="published">{t("status.published")}</option>
            <option value="closed">{t("status.closed")}</option>
            <option value="archived">{t("status.archived")}</option>
          </select>
        </label>
      </div>

      <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {DEMO_SURVEYS.map((survey) => (
          <li key={survey.id} className="flex">
            <SurveyCard survey={survey} />
          </li>
        ))}
      </ul>
    </div>
  );
}
