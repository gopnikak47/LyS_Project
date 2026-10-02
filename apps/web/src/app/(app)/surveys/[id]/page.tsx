import { SurveyBuilder } from "@/components/surveys/survey-builder";
export default async function SurveyPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <SurveyBuilder id={id} />;
}
