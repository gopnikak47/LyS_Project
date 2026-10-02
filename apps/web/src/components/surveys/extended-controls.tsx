"use client";
import {useState} from "react";
import {useTranslations} from "next-intl";
import {api} from "@/lib/api/client";
import type {Question} from "@/lib/api/surveys";

type Props={question:Question;value:unknown;onChange:(v:unknown)=>void;token?:string;slug?:string};

function UploadControl({value,onChange,token,slug}:Props){
  const t=useTranslations("engine");const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  async function upload(file:File|undefined){if(!file||!token||!slug)return;setBusy(true);setError("");try{const form=new FormData();form.append("file",file);form.append("token",token);onChange(await api(`/public/surveys/${slug}/uploads`,{method:"POST",form}));}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  return <div className="space-y-2"><input aria-label={t("types.upload")} type="file" accept=".png,.jpg,.jpeg,.pdf" disabled={!token||busy} onChange={e=>{void upload(e.target.files?.[0]);}}/>{value&&typeof value==="object"&&<p>{String((value as {filename?:string}).filename||"")}</p>}{error&&<p role="alert">{error}</p>}</div>;
}

/** Registry trình render P1, từng loại có component riêng. */
export const EXTENDED_CONTROLS:Partial<Record<Question["type"],React.ComponentType<Props>>>={
  nps:({question:q,value,onChange})=><div className="flex flex-wrap gap-2">{Array.from({length:11},(_,i)=><label className="rounded-lg border p-3" key={i}><input type="radio" name={q.id} checked={value===i} required={q.required} onChange={()=>onChange(i)}/><span className="ml-2">{i}</span></label>)}</div>,
  slider:({question:q,value,onChange})=><div><input aria-label={q.title.vi} className="w-full" type="range" min={Number(q.config.min??0)} max={Number(q.config.max??100)} step={Number(q.config.step??1)} value={typeof value==="number"?value:Number(q.config.min??0)} onChange={e=>onChange(Number(e.target.value))}/><output>{String(value??q.config.min??0)}</output></div>,
  datetime:({question:q,value,onChange})=><input aria-label={q.title.vi} type="datetime-local" required={q.required} className="w-full rounded-lg border p-3" value={typeof value==="string"?value:""} onChange={e=>onChange(e.target.value)}/>,
  contact:({value,onChange})=>{const t=useTranslations("engine");const current=(value||{}) as Record<string,string>;return <div className="grid gap-3">{["name","email","phone"].map(field=><label key={field}>{t(`contactLabels.${field}`)}<input className="block w-full rounded-lg border p-3" type={field==="email"?"email":field==="phone"?"tel":"text"} value={current[field]||""} onChange={e=>onChange({...current,[field]:e.target.value})}/></label>)}</div>;},
  matrix:({question:q,value,onChange})=>{const current=(value||{}) as Record<string,string>;const rows=(q.config.rows||[]) as string[],columns=(q.config.columns||[]) as string[];return <div className="overflow-x-auto"><table className="w-full"><thead><tr><th/><>{columns.map(column=><th className="p-2" key={column}>{column}</th>)}</></tr></thead><tbody>{rows.map(row=><tr key={row}><th className="p-2 text-left">{row}</th>{columns.map(column=><td className="p-2 text-center" key={column}><input aria-label={`${row}: ${column}`} type="radio" name={`${q.id}-${row}`} checked={current[row]===column} required={q.required} onChange={()=>onChange({...current,[row]:column})}/></td>)}</tr>)}</tbody></table></div>;},
  ranking:({question:q,value,onChange})=>{const t=useTranslations("engine");const order=Array.isArray(value)?value as string[]:q.options.map(o=>o.value);function move(index:number,delta:number){const next=[...order];[next[index],next[index+delta]]=[next[index+delta],next[index]];onChange(next);}return <ol className="space-y-2">{order.map((v,i)=><li className="flex items-center justify-between gap-2 rounded-lg border p-2" key={v}><span>{i+1}. {q.options.find(o=>o.value===v)?.label.vi}</span><div className="flex gap-2"><button type="button" disabled={i===0} aria-label={t("moveUp")} onClick={()=>move(i,-1)}>↑</button><button type="button" disabled={i===order.length-1} aria-label={t("moveDown")} onClick={()=>move(i,1)}>↓</button></div></li>)}</ol>;},
  upload:UploadControl,
};
