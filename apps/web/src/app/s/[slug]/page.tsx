import { getTranslations } from "next-intl/server";
import { RespondentForm } from "@/components/surveys/respondent-form";
import type { Survey } from "@/lib/api/surveys";

export default async function PublicSurveyPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const t = await getTranslations("respondent");
  let survey: Survey | null = null;
  let failed = false;
  try {
    const res = await fetch(
      `${process.env.API_INTERNAL_URL || "http://localhost:8000"}/api/v1/public/surveys/${encodeURIComponent(slug)}`,
      { cache: "no-store" },
    );
    survey = res.ok ? await res.json() : null;
  } catch {
    failed = true;
  }
  if (!survey)
    return (
      <main id="main" className="mx-auto max-w-xl px-4 py-20">
        <h1 className="text-2xl font-bold">{t("unavailable")}</h1>
        <p role={failed ? "alert" : undefined}>
          {t(failed ? "networkError" : "unavailableDescription")}
        </p>
      </main>
    );
  return <RespondentForm survey={survey} />;
}
