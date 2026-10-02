import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ComingSoonPage } from "@/components/layout/coming-soon-page";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("app.nav");
  return { title: t("billing") };
}

export default async function BillingPage() {
  const t = await getTranslations("app.nav");
  return <ComingSoonPage title={t("billing")} stage={13} />;
}
