import { getTranslations } from "next-intl/server";
import { RespondentForm } from "@/components/surveys/respondent-form";
import type { Survey } from "@/lib/api/surveys";

export default async function PublicSurveyPage({params}: {params: Promise<{slug: string}>}) {
  const {slug} = await params;
  const t = await getTranslations("respondent");
  let survey: Survey;
  try {
    const res = await fetch(`${process.env.API_INTERNAL_URL || "http://localhost:8000"}/api/v1/public/surveys/${encodeURIComponent(slug)}`, {cache: "no-store"});
    if(!res.ok) return <main id="main" className="mx-auto max-w-xl px-4 py-20"><h1 className="text-2xl font-bold">{t("unavailable")}</h1><p>{t("unavailableDescription")}</p></main>;
    survey = await res.json();
  } catch {return <main id="main" className="mx-auto max-w-xl px-4 py-20"><p role="alert">{t("networkError")}</p></main>;}
  return <RespondentForm survey={survey}/>;
}
