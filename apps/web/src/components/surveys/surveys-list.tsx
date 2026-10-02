"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api/client";
import { useCan, useCurrentWorkspace } from "@/lib/api/hooks";
import type { Page, Survey } from "@/lib/api/surveys";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function SurveysList() {
  const t = useTranslations("engine");
  const { workspace } = useCurrentWorkspace();
  const canEdit = useCan("survey:edit");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({ queryKey: ["surveys", workspace?.id, search, status, page], enabled: !!workspace,
    queryFn: () => api<Page<Survey>>(`/surveys?${new URLSearchParams({ workspace_id: workspace!.id, search, ...(status ? {status} : {}), page: String(page) })}`) });
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h1 className="text-2xl font-bold">{t("surveys")}</h1>{canEdit && <Button asChild><Link href="/surveys/new">{t("create")}</Link></Button>}</div>
    <div className="flex gap-3"><Input aria-label={t("search")} placeholder={t("search")} value={search} onChange={e => {setSearch(e.target.value); setPage(1);}}/>
      <select aria-label={t("status")} value={status} className="rounded-lg border p-2" onChange={e => {setStatus(e.target.value); setPage(1);}}><option value="">{t("all")}</option>{["draft", "published", "closed", "archived"].map(s => <option key={s} value={s}>{t(`statuses.${s}`)}</option>)}</select></div>
    {query.isLoading && <p role="status">{t("loading")}</p>}
    {query.error && <p role="alert">{query.error.message}</p>}
    {!workspace && <p>{t("workspaceRequired")}</p>}
    {query.data?.total === 0 && <p>{t("empty")}</p>}
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{query.data?.items.map(s => <article key={s.id} className="space-y-3 rounded-xl border bg-card p-5">
      <Link className="text-lg font-semibold underline" href={`/surveys/${s.id}`}>{s.title}</Link>
      <p>{t(`statuses.${s.status}`)} · {t("responseCount", { count: s.response_count })}</p><p className="line-clamp-2 text-sm text-muted-foreground">{s.description}</p>
      <Button variant="outline" asChild><Link href={`/surveys/${s.id}`}>{t("open")}</Link></Button>
    </article>)}</div>
    {!!query.data?.total && <div className="flex items-center gap-3"><Button disabled={page === 1} variant="outline" onClick={() => setPage(p => p - 1)}>{t("previous")}</Button><span>{page} / {Math.ceil(query.data.total / 20)}</span><Button variant="outline" disabled={page * 20 >= query.data.total} onClick={() => setPage(p => p + 1)}>{t("next")}</Button></div>}
  </div>;
}
