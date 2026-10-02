"use client";

import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { Copy, MoreHorizontal, Pencil, QrCode, Star, Trash2, XCircle } from "lucide-react";
import type { SurveyStatus } from "@lys/shared";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import type { DemoSurvey } from "@/lib/demo-data";

const STATUS_STYLE: Record<SurveyStatus, string> = {
  draft: "border-border bg-muted text-muted-foreground",
  published: "border-positive/25 bg-positive-soft text-positive-ink",
  closed: "border-neutral/25 bg-neutral-soft text-neutral-ink",
  archived: "border-border bg-muted text-muted-foreground",
};

/** Thẻ khảo sát trong lưới "Khảo sát của tôi" (mục 13.3). */
export function SurveyCard({ survey }: { survey: DemoSurvey }) {
  const t = useTranslations("surveys");
  const tc = useTranslations("common");
  const format = useFormatter();
  const createdAt = format.dateTime(new Date(survey.createdAt), { dateStyle: "medium" });

  return (
    <Card className="group relative w-full gap-0 overflow-hidden py-0 transition-shadow hover:shadow-md">
      <div aria-hidden className={`h-24 bg-gradient-to-br ${survey.cover}`} />
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <h2 className="line-clamp-2 font-semibold">
            <Link
              href={`/surveys/${survey.id}`}
              className="after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:rounded-xl focus-visible:after:ring-[3px] focus-visible:after:ring-ring/50"
            >
              {survey.name}
            </Link>
          </h2>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                className="relative z-10 -mr-1 shrink-0"
                aria-label={tc("moreActions")}
              >
                <MoreHorizontal aria-hidden />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>
                <Pencil aria-hidden />
                {t("menu.edit")}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Copy aria-hidden />
                {t("menu.duplicate")}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <QrCode aria-hidden />
                {t("menu.share")}
              </DropdownMenuItem>
              <DropdownMenuItem>
                <XCircle aria-hidden />
                {t("menu.close")}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive">
                <Trash2 aria-hidden />
                {t("menu.delete")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant="outline" className={STATUS_STYLE[survey.status]}>
            {t(`status.${survey.status}`)}
          </Badge>
          {survey.csat !== null && (
            <span className="inline-flex items-center gap-1 text-muted-foreground">
              <Star className="size-3.5 fill-amber-400 text-amber-400" aria-hidden />
              {t("csat", { value: format.number(survey.csat, { maximumFractionDigits: 1 }) })}
            </span>
          )}
        </div>
        <div className="mt-auto flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-t pt-3 text-xs text-muted-foreground">
          <span>{t("responses", { count: survey.responses })}</span>
          <span>{t("createdAt", { date: createdAt })}</span>
        </div>
      </div>
    </Card>
  );
}

export function SurveyCardSkeleton() {
  return (
    <Card className="w-full gap-0 overflow-hidden py-0" aria-hidden>
      <Skeleton className="h-24 rounded-none" />
      <div className="space-y-3 p-4">
        <Skeleton className="h-5 w-4/5" />
        <Skeleton className="h-5 w-24" />
        <div className="flex justify-between border-t pt-3">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-24" />
        </div>
      </div>
    </Card>
  );
}
