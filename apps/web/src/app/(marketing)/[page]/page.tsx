import Link from "next/link";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { ComingSoonState } from "@/components/feedback/states";

// Các trang nội dung tĩnh chưa xây dựng — trỏ tới giai đoạn sẽ hoàn thiện để không có link chết.
const PLANNED_PAGES = {
  pricing: { stage: 13, title: "marketing.nav.pricing" },
  templates: { stage: 11, title: "marketing.footer.templates" },
  docs: { stage: 14, title: "marketing.footer.docs" },
  about: { stage: 14, title: "marketing.footer.about" },
  privacy: { stage: 14, title: "marketing.footer.privacy" },
  terms: { stage: 14, title: "marketing.footer.terms" },
} as const;

type PlannedPage = keyof typeof PLANNED_PAGES;

export const dynamicParams = false;

export function generateStaticParams() {
  return Object.keys(PLANNED_PAGES).map((page) => ({ page }));
}

export async function generateMetadata({ params }: PageProps<"/[page]">): Promise<Metadata> {
  const { page } = await params;
  const t = await getTranslations();
  return { title: t(PLANNED_PAGES[page as PlannedPage].title) };
}

export default async function PlannedContentPage({ params }: PageProps<"/[page]">) {
  const { page } = await params;
  const entry = PLANNED_PAGES[page as PlannedPage];
  const t = await getTranslations();

  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <h1 className="mb-8 text-3xl font-bold tracking-tight">{t(entry.title)}</h1>
      <ComingSoonState
        title={t("states.comingSoonTitle")}
        description={t("states.comingSoonDescription", { stage: entry.stage })}
        action={
          <Button variant="outline" asChild>
            <Link href="/">{t("states.backHome")}</Link>
          </Button>
        }
      />
    </div>
  );
}
