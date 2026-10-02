"use client";
import {useState} from "react";
import {useQuery,useQueryClient} from "@tanstack/react-query";
import {useTranslations} from "next-intl";
import {api,apiUrl} from "@/lib/api/client";
import {Button} from "@/components/ui/button";

type Usage={plan:string;usage:Record<string,number>;limits:Record<string,number>;plans:{code:string;name:string;price_vnd:number;limits:Record<string,number>}[];can_change:boolean};
export function BillingPanel(){
  const t=useTranslations("billingPanel"),client=useQueryClient();const [error,setError]=useState("");
  const query=useQuery({queryKey:["billing"],queryFn:()=>api<Usage>("/billing/usage")});
  const logs=useQuery({queryKey:["audit"],queryFn:()=>api<{items:{id:string;action:string;created_at:string;entity_type:string}[]}>("/audit-logs")});
  const health=useQuery({queryKey:["observability"],queryFn:()=>api<{analysis_statuses:Record<string,number>}>("/observability"),refetchInterval:10000});
  async function change(code:string){try{await api("/billing/mock-subscription",{method:"POST",body:{plan_code:code}});await client.invalidateQueries({queryKey:["billing"]});}catch(e){setError((e as Error).message);}}
  return <div className="space-y-6"><h1 className="text-2xl font-bold">{t("title")}</h1><p className="rounded-xl border border-primary p-4">{t("mockNotice")}</p>{(error||query.error)&&<p role="alert">{error||query.error?.message}</p>}
    <section className="grid gap-3 sm:grid-cols-4">{["workspaces","members","surveys","nlp_responses_per_month"].map(resource=><article key={resource} className="rounded-xl border bg-card p-5"><h2>{t(`resources.${resource}`)}</h2><p className="text-2xl font-semibold">{query.data?.usage[resource]??"—"} / {query.data?.limits[resource]??"—"}</p></article>)}</section>
    <section className="grid gap-3 sm:grid-cols-3">{query.data?.plans.map(plan=><article className="space-y-3 rounded-xl border bg-card p-5" key={plan.code}><h2 className="text-xl font-semibold">{plan.name}</h2><p>{t("price",{price:plan.price_vnd.toLocaleString("vi-VN")})}</p><Button variant={plan.code===query.data?.plan?"default":"outline"} disabled={!query.data?.can_change||plan.code===query.data?.plan} onClick={()=>{void change(plan.code);}}>{plan.code===query.data?.plan?t("current"):t("simulate")}</Button></article>)}</section>
    <section className="space-y-3 rounded-xl border p-5"><h2 className="text-xl font-semibold">{t("metrics")}</h2>{Object.entries(health.data?.analysis_statuses||{}).map(([status,count])=><p key={status}>{t(`statuses.${status}`)}: {count}</p>)}<a className="underline" href={apiUrl("/metrics")}>{t("prometheus")}</a></section>
    <section className="space-y-3 rounded-xl border p-5"><h2 className="text-xl font-semibold">{t("audit")}</h2><div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr><th>{t("action")}</th><th>{t("time")}</th></tr></thead><tbody>{logs.data?.items.map(log=><tr key={log.id}><td className="border-t p-2">{t.has(`actions.${log.action.replaceAll(".","_")}`)?t(`actions.${log.action.replaceAll(".","_")}`):log.action}</td><td className="border-t p-2">{new Date(log.created_at).toLocaleString("vi-VN")}</td></tr>)}</tbody></table></div></section>
  </div>;
}
