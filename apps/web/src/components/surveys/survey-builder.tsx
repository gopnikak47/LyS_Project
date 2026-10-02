"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { api, apiUrl } from "@/lib/api/client";
import { useCan, useCurrentWorkspace } from "@/lib/api/hooks";
import type { Question, Survey } from "@/lib/api/surveys";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { QuestionControl } from "./question-control";

function QuestionEditor({ question: q, onChange, onRemove }: { question: Question; onChange: (q: Question) => void; onRemove: () => void }) {
  const t = useTranslations("engine");
  const sortable = useSortable({ id: q.id });
  return <div ref={sortable.setNodeRef} style={{ transform: CSS.Transform.toString(sortable.transform), transition: sortable.transition }} className="space-y-3 rounded-xl border bg-card p-4">
    <div className="flex items-center justify-between gap-2"><button type="button" aria-label={t("drag")} {...sortable.attributes} {...sortable.listeners} className="touch-none rounded-lg border px-3 py-2">⠿</button><span>{t(`types.${q.type}`)}</span><Button type="button" variant="outline" onClick={onRemove}>{t("remove")}</Button></div>
    <label className="block space-y-1"><span>{t("questionTitle")}</span><Input value={q.title.vi} onChange={e => onChange({...q, title: {...q.title, vi: e.target.value}})}/></label>
    <label className="flex items-center gap-2"><input type="checkbox" checked={q.required} onChange={e => onChange({...q, required: e.target.checked})}/>{t("required")}</label>
    {q.type === "text" && <label>{t("maxLength")}<Input type="number" min={1} max={10000} value={Number(q.config.max_length || 5000)} onChange={e => onChange({...q, config: {...q.config, max_length: Number(e.target.value)}})}/></label>}
    {(q.type === "single_choice" || q.type === "multi_choice") && <label className="block space-y-1"><span>{t("choices")}</span><textarea className="w-full rounded-lg border p-2" rows={4} value={q.options.map(o => o.label.vi).join("\n")} onChange={e => onChange({...q, options: e.target.value.split("\n").map((label, i) => ({value: q.options[i]?.value || `option-${crypto.randomUUID()}`, label: {vi: label}}))})}/></label>}
  </div>;
}

export function SurveyBuilder({ id }: { id?: string }) {
  const t = useTranslations("engine");
  const router = useRouter();
  const { workspace } = useCurrentWorkspace();
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const query = useQuery({queryKey: ["survey", id], enabled: !!id, queryFn: () => api<Survey>(`/surveys/${id}`)});
  async function create() {
    if (!workspace) return;
    setCreating(true); setError("");
    try {const s = await api<Survey>("/surveys", {method: "POST", body: {workspace_id: workspace.id, title: t("untitled")}}); router.replace(`/surveys/${s.id}`);}
    catch (e) {setError((e as Error).message); setCreating(false);}
  }
  if (!id) return <div className="mx-auto max-w-xl space-y-4 rounded-xl border bg-card p-6"><h1 className="text-2xl font-bold">{t("create")}</h1><p>{workspace?.name || t("workspaceRequired")}</p>{error && <p role="alert">{error}</p>}<Button onClick={create} disabled={!workspace || creating}>{t("create")}</Button></div>;
  if (query.error) return <p role="alert">{query.error.message}</p>;
  if (!query.data) return <p role="status">{t("loading")}</p>;
  return <Editor key={id} initial={query.data}/>;
}

function Editor({initial}: {initial: Survey}) {
  const t = useTranslations("engine");
  const canEdit = useCan("survey:edit");
  const client = useQueryClient();
  const router = useRouter();
  const [draft, setDraft] = useState(initial);
  const [preview, setPreview] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [share, setShare] = useState<{url: string; embed: string} | null>(null);
  const [branch, setBranch] = useState("");
  const [table, setTable] = useState("");
  const latest = useRef(draft); latest.current = draft;
  const version = useRef(initial.updated_at);
  const saved = useRef(JSON.stringify(initial));
  const chain = useRef<Promise<void>>(Promise.resolve());
  const sensors = useSensors(useSensor(PointerSensor, {activationConstraint: {distance: 8}}), useSensor(KeyboardSensor, {coordinateGetter: sortableKeyboardCoordinates}));
  const save = useCallback(() => {
    const run = async () => {
      const current = latest.current;
      if (JSON.stringify(current) === saved.current) return;
      setSaving(true); setError("");
      try {
        const result = await api<Survey>(`/surveys/${initial.id}`, {method: "PUT", body: {...current, expected_updated_at: version.current}});
        version.current = result.updated_at; saved.current = JSON.stringify(current);
        await client.invalidateQueries({queryKey: ["surveys"]});
      } catch(e) {setError((e as Error).message); throw e;}
      finally {setSaving(false);}
    };
    chain.current = chain.current.catch(() => {}).then(run);
    return chain.current;
  }, [initial.id, client]);
  useEffect(() => {
    if (!canEdit) return;
    const timer = setTimeout(() => {void save().catch(() => {});}, 900);
    return () => clearTimeout(timer);
  }, [draft, save, canEdit]);
  useEffect(() => {
    const guard = (e: BeforeUnloadEvent) => {if (saved.current !== JSON.stringify(latest.current)) e.preventDefault();};
    window.addEventListener("beforeunload", guard); return () => window.removeEventListener("beforeunload", guard);
  }, []);
  function add(type: Question["type"]) {
    const id = crypto.randomUUID();
    setDraft(d => ({...d, questions: [...d.questions, {id, code: `q-${id}`, type, title: {vi: t(`types.${type}`)}, description: {}, required: false, config: {}, logic: {}, options: type.includes("choice") ? [{value: "a", label: {vi: t("choiceA")}}, {value: "b", label: {vi: t("choiceB")}}] : []}]}));
  }
  async function action(name: "publish" | "close" | "duplicate") {
    try {await save(); const result = await api<Survey>(`/surveys/${initial.id}/${name}`, {method: "POST"});
      if (name === "duplicate") {router.push(`/surveys/${result.id}`); return;}
      version.current = result.updated_at;
      setDraft(d => ({...d, status: result.status}));
      if (name === "publish") setShare(await api(`/surveys/${initial.id}/share?${new URLSearchParams({branch, table})}`));
    } catch(e) {setError((e as Error).message);}
  }
  return <div className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><h1 className="text-2xl font-bold">{t("builder")}</h1><div className="flex flex-wrap gap-2"><Button variant="outline" onClick={() => setPreview(p => !p)}>{preview ? t("edit") : t("preview")}</Button>{canEdit && <><Button variant="outline" disabled={saving} onClick={() => {void save().catch(() => {});}}>{saving ? t("saving") : t("save")}</Button><Button disabled={saving} onClick={() => {void action("publish");}}>{t("publish")}</Button><Button variant="outline" onClick={() => {void action("close");}}>{t("close")}</Button><Button variant="outline" onClick={() => {void action("duplicate");}}>{t("duplicate")}</Button></>}</div></div>
    {error && <p className="text-destructive" role="alert">{error}</p>}<p role="status">{t(`statuses.${draft.status}`)} · {t("autosave")}</p>
    <fieldset disabled={!canEdit} className="grid gap-5 lg:grid-cols-[1fr_22rem]">
      <div className="space-y-4"><label className="block">{t("title")}<Input value={draft.title} onChange={e => setDraft({...draft, title: e.target.value})}/></label><label className="block">{t("description")}<textarea className="w-full rounded-lg border p-3" value={draft.description || ""} onChange={e => setDraft({...draft, description: e.target.value})}/></label>
        {!preview ? <><div className="flex flex-wrap gap-2">{(["rating", "csat", "text", "single_choice", "multi_choice"] as const).map(type => <Button key={type} type="button" variant="outline" onClick={() => add(type)}>{t(`types.${type}`)}</Button>)}</div>
          <DndContext sensors={sensors} onDragEnd={({active, over}) => {if (over && active.id !== over.id) setDraft(d => ({...d, questions: arrayMove(d.questions, d.questions.findIndex(q => q.id === active.id), d.questions.findIndex(q => q.id === over.id))}));}}><SortableContext items={draft.questions.map(q => q.id)} strategy={verticalListSortingStrategy}><div className="space-y-4">{draft.questions.map(q => <QuestionEditor key={q.id} question={q} onChange={question => setDraft(d => ({...d, questions: d.questions.map(x => x.id === q.id ? question : x)}))} onRemove={() => setDraft(d => ({...d, questions: d.questions.filter(x => x.id !== q.id)}))}/>)}</div></SortableContext></DndContext></> : <div className="space-y-4 rounded-xl p-5" style={{background: draft.theme.background, color: draft.theme.text, fontFamily: draft.theme.font, fontSize: draft.theme.font_size}}>{draft.questions.map(q => <QuestionControl key={q.id} question={q} value={undefined} onChange={() => {}}/>)}</div>}
      </div>
      <aside className="space-y-4 rounded-xl border bg-card p-5"><h2 className="font-semibold">{t("theme")}</h2>{(["primary", "background", "text"] as const).map(key => <label key={key} className="flex justify-between gap-3">{t(`themeLabels.${key}`)}<input type="color" value={draft.theme[key]} onChange={e => setDraft({...draft, theme: {...draft.theme, [key]: e.target.value}})}/></label>)}
        <label className="block">{t("fontSize")}<Input type="number" min={14} max={24} value={draft.theme.font_size} onChange={e => setDraft({...draft, theme: {...draft.theme, font_size: Number(e.target.value)}})}/></label>
        <label className="block">{t("voucherCode")}<Input value={String((draft.settings.voucher as {code?: string} | undefined)?.code || "")} onChange={e => setDraft({...draft, settings: {...draft.settings, voucher: {enabled: !!e.target.value, code: e.target.value || null}}})}/></label>
        <label className="block">{t("branch")}<Input value={branch} onChange={e => setBranch(e.target.value)}/></label><label className="block">{t("table")}<Input value={table} onChange={e => setTable(e.target.value)}/></label>
        <Button type="button" variant="outline" onClick={async () => {try {setShare(await api(`/surveys/${initial.id}/share?${new URLSearchParams({branch, table})}`));} catch(e) {setError((e as Error).message);}}}>{t("share")}</Button>
        {share && <div className="space-y-2 break-all"><a className="underline" href={share.url} target="_blank" rel="noreferrer">{share.url}</a><div className="flex gap-3">{["png", "svg"].map(format => <a className="underline" key={format} href={apiUrl(`/surveys/${initial.id}/qr?${new URLSearchParams({format, branch, table})}`)}>{t("downloadQr", {format: format.toUpperCase()})}</a>)}</div></div>}
      </aside>
    </fieldset>
  </div>;
}
