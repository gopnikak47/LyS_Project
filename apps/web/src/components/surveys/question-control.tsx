"use client";

import { useTranslations } from "next-intl";
import type { Question } from "@/lib/api/surveys";

/** Cùng trình render cho bản xem trước và khách trả lời. */
export function QuestionControl({ question: q, value, onChange, language = "vi", disabled = false }: {
  question: Question; value: unknown; onChange: (value: unknown) => void; language?: string; disabled?: boolean;
}) {
  const t = useTranslations("engine");
  const label = (text: Record<string, string>) => text[language] || text.vi;
  const field = `question-${q.id}`;
  return <fieldset className="space-y-3 rounded-xl border bg-card/90 p-5" disabled={disabled}>
    <legend className="px-2 font-medium">{label(q.title)}{q.required && <span aria-label={t("required")}> *</span>}</legend>
    {label(q.description) && <p className="text-sm">{label(q.description)}</p>}
    {(q.type === "rating" || q.type === "csat") && <div className="flex gap-2" role="radiogroup" aria-label={label(q.title)}>
      {[1, 2, 3, 4, 5].map(n => <label key={n} className="flex cursor-pointer flex-col items-center gap-1 rounded-lg border p-3 has-[:checked]:bg-primary-soft">
        <input type="radio" name={field} value={n} checked={value === n} onChange={() => onChange(n)} required={q.required}/>
        <span aria-hidden>{q.type === "rating" ? "★" : ["😞", "🙁", "😐", "🙂", "😄"][n - 1]}</span><span>{n}</span>
      </label>)}
    </div>}
    {q.type === "text" && <textarea aria-label={label(q.title)} required={q.required} maxLength={Number(q.config.max_length || 5000)} rows={4} className="w-full rounded-lg border bg-background p-3" value={typeof value === "string" ? value : ""} onChange={e => onChange(e.target.value)}/>}
    {(q.type === "single_choice" || q.type === "multi_choice") && q.options.map(option => <label key={option.value} className="flex items-center gap-3 rounded-lg border p-3">
      <input type={q.type === "single_choice" ? "radio" : "checkbox"} name={field} required={q.type === "single_choice" && q.required}
        checked={q.type === "single_choice" ? value === option.value : Array.isArray(value) && value.includes(option.value)}
        onChange={e => onChange(q.type === "single_choice" ? option.value : e.target.checked ? [...(Array.isArray(value) ? value : []), option.value] : (Array.isArray(value) ? value : []).filter(v => v !== option.value))}/>
      {label(option.label)}
    </label>)}
  </fieldset>;
}
