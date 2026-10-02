"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api/client";
import type { Survey } from "@/lib/api/surveys";
import { QuestionControl } from "./question-control";
import {surveyPath} from "@/lib/survey-logic";

export function RespondentForm({survey:initial}: {survey: Survey}) {
  const t = useTranslations("respondent");
  const [survey,setSurvey]=useState(initial);
  const formRef=useRef<HTMLFormElement>(null);
  const [startedAt,setStartedAt]=useState<number|null>(null);
  const [remaining,setRemaining]=useState<number|null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{voucher: string | null; voucher_expires_at: string | null;quiz?:{score:number;maximum:number;classification:string}} | null>(null);
  const [honeypot, setHoneypot] = useState("");
  const [language,setLanguage]=useState(survey.default_language||"vi");
  const [step,setStep]=useState(0);
  const visible=surveyPath(survey.questions,answers);
  const displayed=survey.theme.layout==="one_per_page"?visible.slice(Math.min(step,visible.length-1),Math.min(step,visible.length-1)+1):visible;
  const key = `survey:${initial.slug}:${initial.current_version_id || initial.id}`;
  useEffect(() => {
    let active = true;
    try {const saved = sessionStorage.getItem(key); if(saved) setAnswers(JSON.parse(saved));} catch {}
    type Attempt={token:string;survey:Survey;started_at:number};
    function apply(value:Attempt){setToken(value.token);setSurvey(value.survey);setStartedAt(value.started_at);try{sessionStorage.setItem(`${key}:attempt`,JSON.stringify(value));}catch{}}
    try{const saved=sessionStorage.getItem(`${key}:attempt`);if(saved){const attempt=JSON.parse(saved) as Attempt;if(Date.now()/1000-attempt.started_at<7200){apply(attempt);return()=>{active=false;};}}}catch{}
    void api<Attempt>(`/public/surveys/${initial.slug}/session`, {method: "POST"}).then(value => {if(active)apply(value);}).catch(e => {if(active) setError(e.message);});
    return () => {active = false;};
  }, [initial.slug, key]);
  useEffect(()=>{const duration=Number(survey.settings.quiz_duration_seconds||0);if(!survey.is_quiz||!duration||!startedAt||result)return;const tick=()=>{const left=Math.max(0,Math.ceil(startedAt+duration-Date.now()/1000));setRemaining(left);if(left===0)formRef.current?.requestSubmit();};const timer=setInterval(tick,1000);tick();return()=>clearInterval(timer);},[survey.is_quiz,survey.settings.quiz_duration_seconds,startedAt,result]);
  function change(code: string, value: unknown) {
    const next = {...answers, [code]: value}; setAnswers(next);
    try {sessionStorage.setItem(key, JSON.stringify(next));} catch {}
  }
  async function submit(e: React.FormEvent) {
    e.preventDefault(); if (!token || busy) return;
    for (const q of visible) {
      const value = answers[q.code];
      if(!survey.is_quiz && q.required && (value == null || value === "" || (Array.isArray(value) && !value.length))) {setError(t("required")); return;}
    }
    setBusy(true); setError("");
    const params = new URLSearchParams(window.location.search);
    try {
      let fingerprint="";try{fingerprint=localStorage.getItem("lys.respondent")||crypto.randomUUID();localStorage.setItem("lys.respondent",fingerprint);}catch{}
      const data = await api<NonNullable<typeof result>>(`/public/surveys/${survey.slug}/responses`, {method: "POST", body: {token, answers, honeypot, language, fingerprint, channel: ["qr", "embed", "email", "kiosk", "zalo"].includes(params.get("channel") || "") ? params.get("channel") : "link", source_params: Object.fromEntries(["branch", "table", "invoice"].flatMap(k => params.has(k) ? [[k, params.get(k)!]] : []))}});
      setResult(data); try {sessionStorage.removeItem(key);sessionStorage.removeItem(`${key}:attempt`);} catch {}
    } catch(e) {setError((e as Error).message);}
    finally {setBusy(false);}
  }
  const theme = survey.theme;
  if (result) return <main id="main" className="mx-auto flex min-h-dvh max-w-xl flex-col items-center justify-center gap-5 px-4 text-center"><span aria-hidden className="text-5xl">✓</span><h1 className="text-3xl font-bold">{t("thanks")}</h1><p>{t("thanksDescription")}</p>{result.quiz&&<p>{t("quizResult",result.quiz)}</p>}{result.voucher && <div className="rounded-xl border border-dashed p-6"><p>{t("voucher")}</p><strong className="text-2xl">{result.voucher}</strong>{result.voucher_expires_at && <p>{t("expires", {date: new Date(result.voucher_expires_at).toLocaleDateString("vi-VN")})}</p>}</div>}</main>;
  return <main id="main" className="min-h-dvh px-4 py-8" style={{backgroundColor: theme.background, backgroundImage:theme.background_image?`url(${theme.background_image})`:undefined, backgroundSize:"cover", color: theme.text, fontFamily: theme.font, fontSize: theme.font_size}}><form ref={formRef} noValidate={survey.is_quiz} className="mx-auto max-w-2xl space-y-6" onSubmit={submit}>
    {remaining!==null&&<p role="timer">{t("remaining",{seconds:remaining})}</p>}
    {theme.logo_url&&<img src={theme.logo_url} alt={survey.title} className="h-16 max-w-full object-contain"/>}
    <h1 className="text-3xl font-bold">{survey.title}</h1><p>{survey.description}</p>
    {survey.languages?.length>1&&<label>{t("language")}<select className="ml-2 rounded-lg border p-2" value={language} onChange={e=>setLanguage(e.target.value)}>{survey.languages.map(lang=><option key={lang} value={lang}>{lang==="vi"?"Tiếng Việt":"English"}</option>)}</select></label>}
    <progress className="w-full" aria-label={t("progress")} value={survey.questions.filter(q => answers[q.code] != null && answers[q.code] !== "").length} max={survey.questions.length}/>
    {displayed.map(q => <QuestionControl key={q.id} question={q} value={answers[q.code]} onChange={v => change(q.code, v)} disabled={busy} language={language} token={token} slug={survey.slug}/>)}
    {theme.layout==="one_per_page"&&<div className="flex justify-between"><button type="button" disabled={step===0} onClick={()=>setStep(s=>Math.max(0,s-1))}>{t("previous")}</button><button type="button" disabled={step>=visible.length-1} onClick={()=>{const q=visible[step];if(q?.required&&(answers[q.code]==null||answers[q.code]==="")){setError(t("required"));return;}setError("");setStep(s=>Math.min(visible.length-1,s+1));}}>{t("next")}</button></div>}
    <div hidden aria-hidden><label>{t("honeypot")}<input tabIndex={-1} autoComplete="off" value={honeypot} onChange={e => setHoneypot(e.target.value)}/></label></div>
    {error && <p role="alert" className="text-red-700">{error}</p>}
    <button className="min-h-12 w-full rounded-xl px-5 py-3 text-white disabled:opacity-50" style={{background: theme.primary}} disabled={!token || busy}>{busy ? t("sending") : t("submit")}</button>
  </form></main>;
}
