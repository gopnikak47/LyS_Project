"use client";

import { useCallback, useState, useSyncExternalStore } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Preset = { name: string; values: Record<string, string> };
const changed = "lys.filter-presets";
function subscribe(listener: () => void) {
  window.addEventListener("storage", listener);
  window.addEventListener(changed, listener);
  return () => {
    window.removeEventListener("storage", listener);
    window.removeEventListener(changed, listener);
  };
}
function parse(raw: string): Preset[] {
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return [];
    return value
      .filter(
        (p): p is Preset =>
          typeof p?.name === "string" &&
          p.name.length <= 50 &&
          p.values &&
          typeof p.values === "object" &&
          !Array.isArray(p.values) &&
          Object.values(p.values).every((v) => typeof v === "string" && v.length <= 300),
      )
      .slice(0, 10);
  } catch {
    return [];
  }
}
export function SavedFilters({
  scope,
  values,
  apply,
}: {
  scope: string;
  values: Record<string, string>;
  apply: (values: Record<string, string>) => void;
}) {
  const t = useTranslations("feedbackManager");
  const [name, setName] = useState("");
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const key = `lys.filters:${scope}`;
  const read = useCallback(() => {
    try {
      return localStorage.getItem(key) || "[]";
    } catch {
      return "[]";
    }
  }, [key]);
  const raw = useSyncExternalStore(subscribe, read, () => "[]");
  const presets = parse(raw);
  function write(next: Preset[]) {
    try {
      localStorage.setItem(key, JSON.stringify(next));
      window.dispatchEvent(new Event(changed));
      setError("");
    } catch {
      setError(t("filterStorageError"));
    }
  }
  return (
    <div className="flex flex-wrap items-end gap-2 rounded-lg border p-3">
      <label className="grid gap-1 text-sm">
        {t("savedFilters")}
        <select
          className="rounded border p-2"
          value={selected}
          onChange={(event) => {
            const value = event.target.value;
            setSelected(value);
            const preset = presets.find((p) => p.name === value);
            if (preset) apply(preset.values);
          }}
        >
          <option value="">{t("selectFilter")}</option>
          {presets.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label className="grid gap-1 text-sm">
        {t("filterName")}
        <Input value={name} maxLength={50} onChange={(event) => setName(event.target.value)} />
      </label>
      <Button
        variant="outline"
        disabled={
          !name.trim() || (presets.length >= 10 && !presets.some((p) => p.name === name.trim()))
        }
        onClick={() => {
          write([...presets.filter((p) => p.name !== name.trim()), { name: name.trim(), values }]);
        }}
      >
        {t("saveFilter")}
      </Button>
      <Button
        variant="outline"
        disabled={!selected}
        onClick={() => {
          write(presets.filter((p) => p.name !== selected));
          setSelected("");
        }}
      >
        {t("deleteFilter")}
      </Button>
      {error && <p role="alert">{error}</p>}
    </div>
  );
}
