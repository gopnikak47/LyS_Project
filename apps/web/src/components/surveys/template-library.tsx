"use client";
import {useState} from "react";
import {useQuery} from "@tanstack/react-query";
import {useRouter} from "next/navigation";
import {useTranslations} from "next-intl";
import {api} from "@/lib/api/client";
import type {Survey} from "@/lib/api/surveys";
import {Button} from "@/components/ui/button";

export function TemplateLibrary({workspaceId}:{workspaceId:string}){
  const t=useTranslations("engine"),router=useRouter();const [error,setError]=useState("");const [busy,setBusy]=useState(false);
  const query=useQuery({queryKey:["templates"],queryFn:()=>api<{code:string;title:string;industry:string}[]>("/templates")});
  async function use(code:string){setBusy(true);try{const survey=await api<Survey>(`/templates/${code}/use`,{method:"POST",body:{workspace_id:workspaceId}});router.push(`/surveys/${survey.id}`);}catch(e){setError((e as Error).message);setBusy(false);}}
  return <section className="space-y-4"><h2 className="text-xl font-semibold">{t("templates")}</h2>{error&&<p role="alert">{error}</p>}<div className="grid gap-3 sm:grid-cols-2">{query.data?.map(template=><article className="space-y-2 rounded-lg border p-4" key={template.code}><h3 className="font-medium">{template.title}</h3><p>{template.industry}</p><Button variant="outline" disabled={busy} onClick={()=>{void use(template.code);}}>{t("useTemplate")}</Button></article>)}</div></section>;
}
