"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api/client";
import type { Survey } from "@/lib/api/surveys";
import { QuestionControl } from "./question-control";

export function RespondentForm({survey}: {survey: Survey}) {
  const t = useTranslations("respondent");
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{voucher: string | null; voucher_expires_at: string | null} | null>(null);
  const [honeypot, setHoneypot] = useState("");
  const key = `survey:${survey.slug}:${survey.current_version_id || survey.id}`;
  useEffect(() => {
    let active = true;
    try {const saved = sessionStorage.getItem(key); if(saved) setAnswers(JSON.parse(saved));} catch {}
    void api<{token: string}>(`/public/surveys/${survey.slug}/session`, {method: "POST"}).then(value => {if(active) setToken(value.token);}).catch(e => {if(active) setError(e.message);});
    return () => {active = false;};
  }, [survey.slug, key]);
  function change(code: string, value: unknown) {
    const next = {...answers, [code]: value}; setAnswers(next);
    try {sessionStorage.setItem(key, JSON.stringify(next));} catch {}
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault(); if (!token || busy) return;
    for (const q of survey.questions) {
      const value = answers[q.code];
      if(q.required && (value == null || value === "" || (Array.isArray(value) && !value.length))) {setError(t("required")); return;}
    }
    setBusy(true); setError("");
    const params = new URLSearchParams(window.location.search);
    try {
      const data = await api<{voucher: string | null; voucher_expires_at: string | null}>(`/public/surveys/${survey.slug}/responses`, {method: "POST", body: {token, answers, honeypot, language: "vi", channel: ["qr", "embed", "email", "kiosk", "zalo"].includes(params.get("channel") || "") ? params.get("channel") : "link", source_params: Object.fromEntries(["branch", "table", "invoice"].flatMap(k => params.has(k) ? [[k, params.get(k)!]] : []))}});
      setResult(data); try {sessionStorage.removeItem(key);} catch {}
    } catch(e) {setError((e as Error).message);}
    finally {setBusy(false);}
  }
  const theme = survey.theme;
  if (result) return <main id="main" className="mx-auto flex min-h-dvh max-w-xl flex-col items-center justify-center gap-5 px-4 text-center"><span aria-hidden className="text-5xl">✓</span><h1 className="text-3xl font-bold">{t("thanks")}</h1><p>{t("thanksDescription")}</p>{result.voucher && <div className="rounded-xl border border-dashed p-6"><p>{t("voucher")}</p><strong className="text-2xl">{result.voucher}</strong>{result.voucher_expires_at && <p>{t("expires", {date: new Date(result.voucher_expires_at).toLocaleDateString("vi-VN")})}</p>}</div>}</main>;
  return <main id="main" className="min-h-dvh px-4 py-8" style={{background: theme.background, color: theme.text, fontFamily: theme.font, fontSize: theme.font_size}}><form className="mx-auto max-w-2xl space-y-6" onSubmit={submit}>
    <h1 className="text-3xl font-bold">{survey.title}</h1><p>{survey.description}</p>
    <progress className="w-full" aria-label={t("progress")} value={survey.questions.filter(q => answers[q.code] != null && answers[q.code] !== "").length} max={survey.questions.length}/>
    {survey.questions.map(q => <QuestionControl key={q.id} question={q} value={answers[q.code]} onChange={v => change(q.code, v)} disabled={busy}/>)}
    <div hidden aria-hidden><label>{t("honeypot")}<input tabIndex={-1} autoComplete="off" value={honeypot} onChange={e => setHoneypot(e.target.value)}/></label></div>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    <button className="min-h-12 w-full rounded-xl px-5 py-3 text-white disabled:opacity-50" style={{background: theme.primary}} disabled={!token || busy}>{busy ? t("sending") : t("submit")}</button>
  </form></main>;
}
