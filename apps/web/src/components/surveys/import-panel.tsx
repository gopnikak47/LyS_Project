"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api, apiUrl } from "@/lib/api/client";
import type { Survey } from "@/lib/api/surveys";
import { Button } from "@/components/ui/button";

type Preview = {id: string; columns: string[]; preview: Record<string, string>[]};
type Job = {status: string; processed_rows: number; success_rows: number; error_rows: number; error_message: string | null; has_error_report: boolean};

export function ImportPanel({survey}: {survey: Survey}) {
  const t = useTranslations("imports");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [started, setStarted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const query = useQuery({queryKey: ["import", preview?.id], enabled: !!preview && started, queryFn: () => api<Job>(`/imports/${preview!.id}`), refetchInterval: q => ["done", "failed"].includes(q.state.data?.status || "") ? false : 2000});
  async function upload(file: File | undefined) {
    if (!file) return;
    setBusy(true); setError(""); setStarted(false);
    try {const form = new FormData(); form.append("file", file); setPreview(await api<Preview>(`/imports?survey_id=${survey.id}`, {method: "POST", form})); setMapping({});}
    catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  }
  async function start() {
    setBusy(true); setError("");
    try {await api(`/imports/${preview!.id}/start`, {method: "POST", body: {columns: Object.fromEntries(Object.entries(mapping).filter(([, value]) => !!value))}}); setStarted(true);}
    catch(e) {setError((e as Error).message);} finally {setBusy(false);}
  }
  return <section className="space-y-4 rounded-xl border bg-card p-5"><h2 className="text-xl font-semibold">{t("title")}</h2><p>{t("description")}</p>
    <label className="block">{t("file")}<input type="file" accept=".csv,.xlsx" disabled={busy} onChange={e => {void upload(e.target.files?.[0]);}} className="block w-full rounded-lg border p-3"/></label>
    {error && <p role="alert">{error}</p>}{query.error && <p role="alert">{query.error.message}</p>}
    {preview && !started && <><div className="grid gap-3 sm:grid-cols-2">{survey.questions.map(q => <label key={q.id} className="block">{q.title.vi}{q.required ? " *" : ""}<select className="block w-full rounded-lg border p-2" value={mapping[q.code] || ""} onChange={e => setMapping({...mapping, [q.code]: e.target.value})}><option value="">{t("skip")}</option>{preview.columns.map(column => <option key={column}>{column}</option>)}</select></label>)}</div>
      <div className="overflow-x-auto"><table className="w-full text-sm"><caption>{t("preview")}</caption><thead><tr>{preview.columns.map(c => <th className="p-2 text-left" key={c}>{c}</th>)}</tr></thead><tbody>{preview.preview.map((row, i) => <tr key={i}>{preview.columns.map(c => <td key={c} className="max-w-64 truncate border-t p-2">{row[c]}</td>)}</tr>)}</tbody></table></div><Button disabled={busy} onClick={() => {void start();}}>{t("start")}</Button></>}
    {query.data && <div role="status"><p>{t(`statuses.${query.data.status}`)}</p><p>{t("progress", {processed: query.data.processed_rows, success: query.data.success_rows, errors: query.data.error_rows})}</p>{query.data.error_message && <p>{query.data.error_message}</p>}{query.data.has_error_report && <a className="underline" href={apiUrl(`/imports/${preview!.id}/errors`)}>{t("errors")}</a>}</div>}
  </section>;
}
