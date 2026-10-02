"use client";
import { useTranslations } from "next-intl";
import type { Question, Survey } from "@/lib/api/surveys";
import { api } from "@/lib/api/client";
import { useState } from "react";

type Rule = { question: string; operator: string; value: unknown };
export function LogicEditor({
  question: q,
  questions,
  onChange,
}: {
  question: Question;
  questions: Question[];
  onChange: (q: Question) => void;
}) {
  const t = useTranslations("engine");
  const index = questions.findIndex((v) => v.id === q.id),
    previous = questions.slice(0, index);
  const display = (q.logic.display_if || {}) as { all?: Rule[]; any?: Rule[] };
  const mode = display.any ? "any" : "all",
    rules = display[mode] || [];
  function updateRule(i: number, patch: Partial<Rule>) {
    const next = rules.map((r, n) => (n === i ? { ...r, ...patch } : r));
    onChange({ ...q, logic: { ...q.logic, display_if: { [mode]: next } } });
  }
  return (
    <details className="rounded-lg border p-3">
      <summary className="cursor-pointer">{t("logic")}</summary>
      <div className="mt-3 space-y-3">
        <p>{t("logicHint")}</p>
        <label>
          {t("displayMode")}
          <select
            className="ml-2 rounded border p-2"
            value={mode}
            onChange={(e) =>
              onChange({ ...q, logic: { ...q.logic, display_if: { [e.target.value]: rules } } })
            }
          >
            <option value="all">{t("allConditions")}</option>
            <option value="any">{t("anyCondition")}</option>
          </select>
        </label>
        {rules.map((r, i) => (
          <div className="grid gap-2 sm:grid-cols-3" key={i}>
            <select
              aria-label={t("sourceQuestion")}
              className="rounded border p-2"
              value={r.question}
              onChange={(e) => updateRule(i, { question: e.target.value })}
            >
              {previous.map((p) => (
                <option value={p.code} key={p.id}>
                  {p.title.vi}
                </option>
              ))}
            </select>
            <select
              aria-label={t("operator")}
              className="rounded border p-2"
              value={r.operator}
              onChange={(e) => updateRule(i, { operator: e.target.value })}
            >
              {["eq", "ne", "contains", "gt", "lt"].map((op) => (
                <option key={op} value={op}>
                  {t(`operators.${op}` as Parameters<typeof t>[0])}
                </option>
              ))}
            </select>
            <input
              aria-label={t("conditionValue")}
              className="rounded border p-2"
              value={String(r.value ?? "")}
              onChange={(e) => {
                const value = e.target.value;
                updateRule(i, { value: /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : value });
              }}
            />
          </div>
        ))}
        <div className="flex gap-3">
          <button
            type="button"
            className="underline"
            disabled={!previous.length}
            onClick={() =>
              onChange({
                ...q,
                logic: {
                  ...q.logic,
                  display_if: {
                    [mode]: [...rules, { question: previous[0]?.code, operator: "eq", value: "" }],
                  },
                },
              })
            }
          >
            {t("addCondition")}
          </button>
          <button
            type="button"
            className="underline"
            onClick={() => onChange({ ...q, logic: { ...q.logic, display_if: {} } })}
          >
            {t("clearConditions")}
          </button>
        </div>
        <label className="block">
          {t("carry")}
          <select
            className="block w-full rounded border p-2"
            value={String(q.logic.carry_from || "")}
            onChange={(e) =>
              onChange({ ...q, logic: { ...q.logic, carry_from: e.target.value || null } })
            }
          >
            <option value="">{t("none")}</option>
            {previous
              .filter((p) => p.options.length)
              .map((p) => (
                <option value={p.code} key={p.id}>
                  {p.title.vi}
                </option>
              ))}
          </select>
        </label>
        <label className="block">
          {t("jumpValue")}
          <input
            className="block w-full rounded border p-2"
            value={String(((q.logic.jumps as { if: Rule }[]) || [])[0]?.if.value ?? "")}
            onChange={(e) => {
              const jumps = (q.logic.jumps as { if: Rule; target: string }[]) || [];
              onChange({
                ...q,
                logic: {
                  ...q.logic,
                  jumps: [
                    {
                      if: {
                        question: q.code,
                        operator: "eq",
                        value: /^\d+$/.test(e.target.value)
                          ? Number(e.target.value)
                          : e.target.value,
                      },
                      target: jumps[0]?.target || "end",
                    },
                  ],
                },
              });
            }}
          />
        </label>
        <label className="block">
          {t("jumpTarget")}
          <select
            className="block w-full rounded border p-2"
            value={((q.logic.jumps as { target: string }[]) || [])[0]?.target || ""}
            onChange={(e) => {
              const first = ((q.logic.jumps as { if: Rule; target: string }[]) || [])[0];
              onChange({
                ...q,
                logic: {
                  ...q.logic,
                  jumps: e.target.value
                    ? [
                        {
                          if: first?.if || { question: q.code, operator: "eq", value: "" },
                          target: e.target.value,
                        },
                      ]
                    : [],
                },
              });
            }}
          >
            <option value="">{t("none")}</option>
            <option value="end">{t("endSurvey")}</option>
            {questions.slice(index + 1).map((p) => (
              <option key={p.id} value={p.code}>
                {p.title.vi}
              </option>
            ))}
          </select>
        </label>
      </div>
    </details>
  );
}

export function AdvancedSettings({
  survey: s,
  onChange,
}: {
  survey: Survey;
  onChange: (s: Survey) => void;
}) {
  const t = useTranslations("engine");
  const settings = s.settings;
  const [error, setError] = useState("");
  async function asset(file: File | undefined, field: "logo_url" | "background_image") {
    if (!file) return;
    try {
      const form = new FormData();
      form.append("file", file);
      const result = await api<{ url: string }>(`/surveys/${s.id}/assets`, {
        method: "POST",
        form,
      });
      onChange({ ...s, theme: { ...s.theme, [field]: result.url } });
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <details className="space-y-3">
      <summary>{t("advanced")}</summary>
      <div className="space-y-3">
        <label className="block">
          {t("layout")}
          <select
            className="block rounded border p-2"
            value={s.theme.layout}
            onChange={(e) =>
              onChange({
                ...s,
                theme: { ...s.theme, layout: e.target.value as "scroll" | "one_per_page" },
              })
            }
          >
            <option value="scroll">{t("scroll")}</option>
            <option value="one_per_page">{t("onePerPage")}</option>
          </select>
        </label>
        {(["logo_url", "background_image"] as const).map((field) => (
          <label className="block" key={field}>
            {t(field as Parameters<typeof t>[0])}
            <input
              type="file"
              className="w-full"
              accept=".png,.jpg,.jpeg"
              onChange={(e) => {
                void asset(e.target.files?.[0], field);
              }}
            />
          </label>
        ))}
        {error && <p role="alert">{error}</p>}
        <label className="block">
          {t("font")}
          <select
            className="block rounded border p-2"
            value={s.theme.font}
            onChange={(e) =>
              onChange({
                ...s,
                theme: { ...s.theme, font: e.target.value as "sans-serif" | "serif" },
              })
            }
          >
            <option value="sans-serif">{t("sans")}</option>
            <option value="serif">{t("serif")}</option>
          </select>
        </label>
        <label className="flex gap-2">
          <input
            type="checkbox"
            checked={s.is_quiz}
            onChange={(e) => onChange({ ...s, is_quiz: e.target.checked })}
          />
          {t("quiz")}
        </label>
        {s.is_quiz &&
          (["quiz_duration_seconds", "quiz_draw_count"] as const).map((field) => (
            <label className="block" key={field}>
              {t(field as Parameters<typeof t>[0])}
              <input
                className="w-full rounded border p-2"
                type="number"
                min={field === "quiz_duration_seconds" ? 30 : 1}
                value={String(settings[field] || "")}
                onChange={(e) => {
                  const next = { ...settings };
                  if (e.target.value) next[field] = Number(e.target.value);
                  else delete next[field];
                  onChange({ ...s, settings: next });
                }}
              />
            </label>
          ))}
        {["randomize_questions", "randomize_options"].map((field) => (
          <label className="flex gap-2" key={field}>
            <input
              type="checkbox"
              checked={!!settings[field]}
              onChange={(e) =>
                onChange({ ...s, settings: { ...settings, [field]: e.target.checked } })
              }
            />
            {t(field as Parameters<typeof t>[0])}
          </label>
        ))}
        <label className="flex gap-2">
          <input
            type="checkbox"
            checked={s.languages.includes("en")}
            onChange={(e) =>
              onChange({
                ...s,
                languages: e.target.checked ? ["vi", "en"] : ["vi"],
                default_language: "vi",
              })
            }
          />
          {t("bilingual")}
        </label>
        {(["opens_at", "closes_at"] as const).map((field) => (
          <label className="block" key={field}>
            {t(field as Parameters<typeof t>[0])}
            <input
              className="block w-full rounded border p-2"
              type="datetime-local"
              value={
                s[field]
                  ? new Date(new Date(s[field]!).getTime() - new Date().getTimezoneOffset() * 60000)
                      .toISOString()
                      .slice(0, 16)
                  : ""
              }
              onChange={(e) =>
                onChange({
                  ...s,
                  [field]: e.target.value ? new Date(e.target.value).toISOString() : null,
                })
              }
            />
          </label>
        ))}
        <label className="block">
          {t("maxResponses")}
          <input
            className="block w-full rounded border p-2"
            type="number"
            min={1}
            value={String(settings.max_responses || "")}
            onChange={(e) => {
              const next = { ...settings };
              if (e.target.value) next.max_responses = Number(e.target.value);
              else delete next.max_responses;
              onChange({ ...s, settings: next });
            }}
          />
        </label>
        {["one_per_ip", "one_per_browser"].map((field) => (
          <label className="flex gap-2" key={field}>
            <input
              type="checkbox"
              checked={!!settings[field]}
              onChange={(e) =>
                onChange({ ...s, settings: { ...settings, [field]: e.target.checked } })
              }
            />
            {t(field as Parameters<typeof t>[0])}
          </label>
        ))}
      </div>
    </details>
  );
}
