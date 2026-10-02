import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { MessageSquareText, Plus, RotateCw, Smile, Star, TriangleAlert } from "lucide-react";
import { KpiCard, KpiCardSkeleton } from "@/components/feedback/kpi-card";
import { SentimentBadge, UrgentBadge } from "@/components/feedback/sentiment-badge";
import { EmptyState, ErrorState } from "@/components/feedback/states";
import { TopicChip } from "@/components/feedback/topic-chip";
import { PageHeader } from "@/components/layout/page-header";
import { ResponsesTableDemo, TableSkeleton } from "@/components/ui-kit/responses-table-demo";
import { SurveyFormDemo } from "@/components/ui-kit/survey-form-demo";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { DEMO_RESPONSES } from "@/lib/demo-data";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("uiKit");
  return { title: t("title") };
}

function Section({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="space-y-4">
      <h2 id={id} className="text-lg font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

export default async function UiKitPage() {
  const t = await getTranslations("uiKit");
  const ts = await getTranslations("states");
  const tc = await getTranslations("common");

  return (
    <div className="space-y-12">
      <PageHeader title={t("title")} description={t("subtitle")} />

      <Section id="kit-buttons" title={t("buttons")}>
        <div className="flex flex-wrap items-center gap-3">
          <Button>
            <Plus aria-hidden />
            {t("primary")}
          </Button>
          <Button variant="secondary">{t("secondary")}</Button>
          <Button variant="outline">{t("outline")}</Button>
          <Button variant="ghost">{t("ghost")}</Button>
          <Button variant="destructive">{t("destructive")}</Button>
          <Button size="sm">sm</Button>
          <Button size="lg">lg</Button>
          <Button size="xl">xl</Button>
          <Button disabled>{t("primary")}</Button>
        </div>
      </Section>

      <Section id="kit-badges" title={t("badges")}>
        <div className="flex flex-wrap items-center gap-2">
          <SentimentBadge sentiment="positive" confidence={0.95} />
          <SentimentBadge sentiment="negative" confidence={0.88} />
          <SentimentBadge sentiment="neutral" confidence={0.62} />
          <UrgentBadge />
          <TopicChip label="Món ăn" color="oklch(0.65 0.17 50)" />
          <TopicChip label="Phục vụ" color="oklch(0.55 0.18 300)" />
          <TopicChip label="Vệ sinh" color="oklch(0.6 0.15 200)" />
        </div>
      </Section>

      <Section id="kit-kpis" title={t("kpis")}>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <KpiCard
            label={t("kpi.total")}
            value="2.418"
            icon={MessageSquareText}
            delta={12}
            deltaLabel={t("kpi.vsPrevious")}
          />
          <KpiCard
            label={t("kpi.csat")}
            value="4,4"
            icon={Star}
            delta={3}
            deltaLabel={t("kpi.vsPrevious")}
          />
          <KpiCard
            label={t("kpi.positive")}
            value="71%"
            icon={Smile}
            tone="positive"
            delta={-2}
            deltaLabel={t("kpi.vsPrevious")}
          />
          <KpiCard
            label={t("kpi.urgent")}
            value="3"
            icon={TriangleAlert}
            tone="urgent"
            delta={50}
            higherIsBetter={false}
            deltaLabel={t("kpi.vsPrevious")}
          />
        </div>
        <p className="text-xs text-muted-foreground">{tc("demoData")}</p>
      </Section>

      <Section id="kit-table" title={t("table")}>
        <ResponsesTableDemo rows={DEMO_RESPONSES} />
      </Section>

      <Section id="kit-form" title={t("form")}>
        <Card className="max-w-2xl">
          <CardContent>
            <SurveyFormDemo />
          </CardContent>
        </Card>
      </Section>

      <Section id="kit-skeleton" title={t("skeleton")}>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <KpiCardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton />
      </Section>

      <Section id="kit-states" title={t("states")}>
        <div className="grid gap-4 md:grid-cols-2">
          <EmptyState
            title={ts("emptyTitle")}
            description={ts("emptyDescription")}
            action={
              <Button variant="outline" size="sm">
                <Plus aria-hidden />
                {tc("create")}
              </Button>
            }
          />
          <ErrorState
            title={ts("errorTitle")}
            description={ts("errorDescription")}
            action={
              <Button variant="outline" size="sm">
                <RotateCw aria-hidden />
                {tc("retry")}
              </Button>
            }
          />
        </div>
      </Section>
    </div>
  );
}
