import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { TopicsManager } from "@/components/topics/topics-manager";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("topics");
  return { title: t("title") };
}

export default function TopicsPage() {
  return <TopicsManager />;
}
