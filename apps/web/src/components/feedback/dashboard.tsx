"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api, apiUrl } from "@/lib/api/client";
import { useCan, useCurrentWorkspace } from "@/lib/api/hooks";
import type { Page, Survey } from "@/lib/api/surveys";
import { Button } from "@/components/ui/button";
import {ReportTools} from "./report-tools";
import { Input } from "@/components/ui/input";

type Overview = {total_responses: number; csat: number | null; completion_rate: number | null; analyzed_texts: number; urgent_responses: number; sentiments: Record<string,{count:number;percent:number|null}>};
type Trend = {date: string; responses: number; csat: number | null};
type TopicTrend = {date: string; topic_id: string; count: number};
type Word = {word: string; sentiment: string; count: number};
type Export = {id: string; status: string; ready: boolean; error_message: string | null};

export function Dashboard() {
  const t = useTranslations("dashboard");
  const {workspace} = useCurrentWorkspace(); const client=useQueryClient(); const canExport=useCan("data:export");
  const [start,setStart]=useState(""); const [end,setEnd]=useState(""); const [surveyId,setSurveyId]=useState(""); const [period,setPeriod]=useState("week");
  const [job,setJob]=useState<string|null>(null); const [error,setError]=useState("");
  const params=new URLSearchParams({workspace_id:workspace?.id||""});
  if(start)params.set("start",new Date(`${start}T00:00:00`).toISOString());if(end)params.set("end",new Date(`${end}T00:00:00`).toISOString());if(surveyId)params.set("survey_id",surveyId);
  const filter=params.toString();
  const overview=useQuery({queryKey:["overview",filter],enabled:!!workspace,queryFn:()=>api<Overview>(`/analytics/overview?${filter}`),refetchInterval:20000});
  const trends=useQuery({queryKey:["trends",filter,period],enabled:!!workspace,queryFn:()=>api<Trend[]>(`/analytics/trends?${filter}&period=${period}`),refetchInterval:20000});
  const topics=useQuery({queryKey:["topic-trends",filter,period],enabled:!!workspace,queryFn:()=>api<TopicTrend[]>(`/analytics/topics?${filter}&period=${period}`),refetchInterval:20000});
  const catalog=useQuery({queryKey:["topics",workspace?.id],enabled:!!workspace,queryFn:()=>api<{topics:{id:string;name:string;color:string}[]}>(`/workspaces/${workspace!.id}/topics`)});
  const words=useQuery({queryKey:["wordcloud",filter],enabled:!!workspace,queryFn:()=>api<Word[]>(`/analytics/wordcloud?${filter}`),refetchInterval:20000});
  const surveys=useQuery({queryKey:["survey-options",workspace?.id],enabled:!!workspace,queryFn:()=>api<Page<Survey>>(`/surveys?workspace_id=${workspace!.id}&page_size=100`)});
  const report=useQuery({queryKey:["export",job],enabled:!!job,queryFn:()=>api<Export>(`/exports/${job}`),refetchInterval:q=>["done","failed"].includes(q.state.data?.status||"")?false:2000});
  useEffect(()=>{if(!workspace)return;const stream=new EventSource(apiUrl(`/analytics/events?${filter}`),{withCredentials:true});stream.addEventListener("overview",e=>{try{client.setQueryData(["overview",filter],JSON.parse((e as MessageEvent).data));}catch{}});stream.addEventListener("expired",()=>stream.close());stream.onerror=()=>stream.close();return()=>stream.close();},[filter,workspace,client]);
  async function exportReport(kind:string){setError("");try{const result=await api<Export>("/exports",{method:"POST",body:{kind,filters:Object.fromEntries(params)}});setJob(result.id);}catch(e){setError((e as Error).message);}}
  const data=overview.data; const percent=(value:number|null|undefined)=>value==null?"—":`${Math.round(value*100)}%`;
  const maximum=Math.max(1,...(trends.data||[]).map(row=>row.responses));
  const buckets=[...new Set((topics.data||[]).map(row=>row.date))].sort(); const latest=buckets.at(-1); const previous=buckets.at(-2);
  return <div className="space-y-6"><div className="flex flex-wrap items-center justify-between gap-3"><h1 className="text-2xl font-bold">{t("title")}</h1>{canExport&&<div className="flex gap-2">{["xlsx","pdf"].map(kind=><Button key={kind} variant="outline" onClick={()=>{void exportReport(kind);}}>{t("export",{kind:kind.toUpperCase()})}</Button>)}</div>}</div>
    <div className="grid gap-3 sm:grid-cols-4"><label>{t("start")}<Input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label><label>{t("end")}<Input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label><label>{t("survey")}<select className="block w-full rounded-lg border p-2" value={surveyId} onChange={e=>setSurveyId(e.target.value)}><option value="">{t("allSurveys")}</option>{surveys.data?.items.map(s=><option value={s.id} key={s.id}>{s.title}</option>)}</select></label><label>{t("period")}<select className="block w-full rounded-lg border p-2" value={period} onChange={e=>setPeriod(e.target.value)}>{["week","month","quarter"].map(p=><option value={p} key={p}>{t(`periods.${p}`)}</option>)}</select></label></div>
    {(error||overview.error||report.error)&&<p role="alert">{error||overview.error?.message||report.error?.message}</p>}{overview.isLoading&&<p role="status">{t("loading")}</p>}
    {report.data&&<div role="status" className="rounded-xl border p-4">{report.data.ready?<a href={apiUrl(`/exports/${job}/download`)} className="underline">{t("download")}</a>:report.data.status==="failed"?t("exportFailed"):t("exportPending")}{report.data.error_message&&<p>{report.data.error_message}</p>}</div>}
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{[["total",data?.total_responses??"—"],["csat",data?.csat?.toFixed(2)??"—"],["urgent",data?.urgent_responses??"—"],["completion",percent(data?.completion_rate)]].map(([label,value])=><article key={label} className="rounded-xl border bg-card p-5"><p className="text-muted-foreground">{t(String(label))}</p><p className="mt-2 text-3xl font-semibold">{value}</p></article>)}</div>
    <section className="rounded-xl border bg-card p-5"><h2 className="text-xl font-semibold">{t("sentimentsTitle")}</h2><p className="text-sm text-muted-foreground">{t("sentimentsNote")}</p><div className="mt-4 grid gap-4 sm:grid-cols-3">{["positive","negative","neutral"].map(label=><div key={label} className={label==="positive"?"text-green-700":label==="negative"?"text-red-700":"text-muted-foreground"}><p>{t(`sentiments.${label}`)}</p><strong className="text-2xl">{percent(data?.sentiments[label]?.percent)}</strong><p>{data?.sentiments[label]?.count??0}</p></div>)}</div></section>
    <section className="space-y-4 rounded-xl border bg-card p-5"><h2 className="text-xl font-semibold">{t("trends")}</h2>{trends.data?.length===0&&<p>{t("empty")}</p>}<div className="flex h-56 items-end gap-2 overflow-x-auto pb-8">{trends.data?.map(row=><div key={row.date} className="relative flex h-full min-w-12 flex-1 items-end" title={`${new Date(row.date).toLocaleDateString("vi-VN")}: ${row.responses}`}><div className="w-full rounded-t bg-primary" style={{height:`${Math.max(2,row.responses/maximum*100)}%`}}><span className="block text-center text-sm text-primary-foreground">{row.responses}</span></div><span className="absolute -bottom-7 w-full text-center text-xs">{new Date(row.date).toLocaleDateString("vi-VN",{month:"2-digit",day:"2-digit"})}</span></div>)}</div></section>
    <section className="space-y-4 rounded-xl border bg-card p-5"><h2 className="text-xl font-semibold">{t("topics")}</h2><p>{t("anomalyNote")}</p>{catalog.data?.topics.map(topic=>{const current=topics.data?.find(r=>r.topic_id===topic.id&&r.date===latest)?.count||0;const before=topics.data?.find(r=>r.topic_id===topic.id&&r.date===previous)?.count||0;return <div key={topic.id} className="flex flex-wrap items-center gap-3"><span className="size-3 rounded-full" style={{background:topic.color}}/><Link href={`/responses?topic_id=${topic.id}`} className="underline">{topic.name}</Link><span>{current}</span>{previous&&current>=5&&current>before*2&&<span className="text-orange-700">{t("spike")}</span>}<div className="flex items-end gap-1">{buckets.map(date=><span key={date} className="w-4 rounded-t" title={`${date}: ${topics.data?.find(r=>r.topic_id===topic.id&&r.date===date)?.count||0}`} style={{background:topic.color,height:Math.max(2,Math.min(40,(topics.data?.find(r=>r.topic_id===topic.id&&r.date===date)?.count||0)*2))}}/>)}</div></div>;})}</section>
    <div className="grid gap-4 md:grid-cols-2">{["positive","negative"].map(sentiment=><section className="rounded-xl border bg-card p-5" key={sentiment}><h2 className="text-xl font-semibold">{t(sentiment==="positive"?"praise":"complaints")}</h2><div className="mt-4 flex flex-wrap items-center gap-3">{words.data?.filter(w=>w.sentiment===sentiment).map(w=><Link className={sentiment==="positive"?"text-green-700":"text-red-700"} style={{fontSize:Math.min(34,14+Math.log2(w.count+1)*3)}} key={w.word} href={`/responses?search=${encodeURIComponent(w.word)}&sentiment=${sentiment}`} title={String(w.count)}>{w.word.replaceAll("_"," ")}</Link>)}</div></section>)}</div>
    {workspace&&<ReportTools workspaceId={workspace.id} filter={filter}/>}
  </div>;
}
