import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { ArrowRight, BarChart3, Share2, Sparkles, Wrench } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import { FeatureTabs } from "@/components/marketing/feature-tabs";
import { HeroPreview } from "@/components/marketing/hero-preview";

export default async function LandingPage() {
  const t = await getTranslations("marketing");

  const steps = [
    { key: "setup", icon: Wrench },
    { key: "share", icon: Share2 },
    { key: "report", icon: BarChart3 },
  ] as const;

  const stats = [
    { value: "5+", label: t("stats.questionTypes") },
    { value: "6", label: t("stats.industries") },
    { value: "3", label: t("stats.sentiments") },
    { value: "4", label: t("stats.channels") },
  ];

  const faqs = (["1", "2", "3", "4"] as const).map((n) => ({
    id: `faq-${n}`,
    q: t(`faq.q${n}`),
    a: t(`faq.a${n}`),
  }));

  return (
    <>
      {/* ---------------- Hero ---------------- */}
      <section className="relative overflow-hidden">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 pt-12 pb-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:px-8 lg:pt-20 lg:pb-24">
          <div className="space-y-6">
            <p className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1 text-xs font-medium text-muted-foreground shadow-soft">
              <Sparkles className="size-3.5 text-primary" aria-hidden />
              {t("hero.eyebrow")}
            </p>
            <h1 className="text-4xl leading-tight font-bold tracking-tight text-balance sm:text-5xl lg:text-6xl">
              {t("hero.title")}
            </h1>
            <p className="max-w-xl text-lg text-pretty text-muted-foreground">
              {t("hero.subtitle")}
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button size="xl" asChild>
                <Link href="/register">
                  {t("hero.cta")}
                  <ArrowRight aria-hidden />
                </Link>
              </Button>
              <Button size="xl" variant="outline" asChild>
                <Link href="#steps">{t("hero.secondaryCta")}</Link>
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">{t("hero.note")}</p>
          </div>
          <HeroPreview />
        </div>
      </section>

      {/* ---------------- Tính năng ---------------- */}
      <section id="features" className="scroll-mt-20 border-y bg-card/50 py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto mb-10 max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">{t("features.title")}</h2>
            <p className="mt-3 text-muted-foreground">{t("features.subtitle")}</p>
          </div>
          <FeatureTabs />
        </div>
      </section>

      {/* ---------------- 3 bước ---------------- */}
      <section id="steps" className="scroll-mt-20 py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="mb-10 text-center text-3xl font-bold tracking-tight sm:text-4xl">
            {t("steps.title")}
          </h2>
          <ol className="grid gap-6 md:grid-cols-3">
            {steps.map(({ key, icon: Icon }, index) => (
              <li key={key} className="relative rounded-2xl border bg-card p-6 shadow-soft">
                <span
                  className="absolute top-6 right-6 text-5xl font-bold text-muted/80 select-none"
                  aria-hidden
                >
                  {index + 1}
                </span>
                <span className="mb-4 grid size-11 place-items-center rounded-xl bg-primary text-primary-foreground">
                  <Icon className="size-5" aria-hidden />
                </span>
                <h3 className="text-lg font-semibold">
                  <span className="sr-only">{index + 1}. </span>
                  {t(`steps.${key}.title`)}
                </h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {t(`steps.${key}.description`)}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ---------------- Số liệu nổi bật ---------------- */}
      <section className="bg-primary py-14 text-primary-foreground">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="text-center text-2xl font-semibold">{t("stats.title")}</h2>
          <dl className="mt-8 grid grid-cols-2 gap-6 text-center md:grid-cols-4">
            {stats.map((stat) => (
              <div key={stat.label} className="flex flex-col-reverse gap-1">
                <dt className="text-sm opacity-90">{stat.label}</dt>
                <dd className="text-4xl font-bold tabular-nums">{stat.value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-6 text-center text-xs opacity-80">{t("stats.note")}</p>
        </div>
      </section>

      {/* ---------------- FAQ ---------------- */}
      <section id="faq" className="scroll-mt-20 py-16 sm:py-24">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <h2 className="mb-8 text-center text-3xl font-bold tracking-tight sm:text-4xl">
            {t("faq.title")}
          </h2>
          <Accordion
            type="single"
            collapsible
            className="rounded-2xl border bg-card px-6 shadow-soft"
          >
            {faqs.map((faq) => (
              <AccordionItem key={faq.id} value={faq.id}>
                <AccordionTrigger className="text-base">{faq.q}</AccordionTrigger>
                <AccordionContent className="text-muted-foreground">{faq.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>

      {/* ---------------- CTA cuối ---------------- */}
      <section className="px-4 pb-20 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-5xl flex-col items-center gap-6 rounded-3xl bg-gradient-to-br from-primary to-indigo-700 px-6 py-12 text-center text-primary-foreground shadow-soft sm:py-16">
          <h2 className="text-2xl font-bold text-balance sm:text-3xl">{t("cta.title")}</h2>
          <Button size="xl" variant="secondary" asChild>
            <Link href="/register">
              {t("cta.button")}
              <ArrowRight aria-hidden />
            </Link>
          </Button>
        </div>
      </section>
    </>
  );
}
