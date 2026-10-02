"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api, apiUrl } from "@/lib/api/client";
import { useCan, useCurrentWorkspace } from "@/lib/api/hooks";
import type { Page } from "@/lib/api/surveys";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

type Feedback = {
  id: string;
  text: string;
  rating: number | null;
  sentiment: string | null;
  sentiment_score: number | null;
  topic_ids: string[];
  is_urgent: boolean;
  urgent_reasons: string[];
  channel: string;
  responded_at: string;
  status: string;
  note: string | null;
  updated_at: string;
  is_verified: boolean;
};
type Topic = { id: string; name: string };
type History = {
  id: string;
  field: string;
  old_value: unknown;
  new_value: unknown;
  reason: string;
  reverted_at: string | null;
  review_status: string;
};

export function FeedbackManager() {
  const t = useTranslations("feedbackManager");
  const { workspace } = useCurrentWorkspace();
  const client = useQueryClient();
  const canEdit = useCan("label:edit");
  const canExport = useCan("data:export");
  const [search, setSearch] = useState("");
  const [sentiment, setSentiment] = useState("");
  const [urgent, setUrgent] = useState(false);
  const [topic, setTopic] = useState("");
  useEffect(() => {
    // Restore URL filters after hydration; the URL is external browser state.
    queueMicrotask(() => {
      const p = new URLSearchParams(window.location.search);
      setSearch(p.get("search") || "");
      setSentiment(p.get("sentiment") || "");
      setTopic(p.get("topic_id") || "");
    });
  }, []);
  const [channel, setChannel] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [sort, setSort] = useState("urgent");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<string | null>(null);
  const [checked, setChecked] = useState<string[]>([]);
  const [error, setError] = useState("");
  const params = new URLSearchParams({
    workspace_id: workspace?.id || "",
    page: String(page),
    search,
    sort,
  });
  if (sentiment) params.set("sentiment", sentiment);
  if (urgent) params.set("urgent", "true");
  if (topic) params.set("topic_id", topic);
  if (channel) params.set("channel", channel);
  if (start) params.set("start", new Date(`${start}T00:00:00`).toISOString());
  if (end) params.set("end", new Date(`${end}T00:00:00`).toISOString());
  const query = useQuery({
    queryKey: ["feedback", workspace?.id, params.toString()],
    enabled: !!workspace,
    queryFn: () => api<Page<Feedback>>(`/responses?${params}`),
  });
  const topics = useQuery({
    queryKey: ["topics", workspace?.id],
    enabled: !!workspace,
    queryFn: () => api<{ topics: Topic[] }>(`/workspaces/${workspace!.id}/topics`),
  });
  const quality = useQuery({
    queryKey: ["quality", workspace?.id],
    enabled: !!workspace,
    queryFn: () =>
      api<{ total: number; verified: number; corrected: number; correction_rate: number | null }>(
        `/model-quality?workspace_id=${workspace!.id}`,
      ),
  });
  useEffect(() => {
    if (!selected) return;
    const move = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.closest("input,textarea,select,[contenteditable]")) return;
      const items = query.data?.items || [];
      const index = items.findIndex((r) => r.id === selected);
      if (e.key === "n") setSelected(items[index + 1]?.id || selected);
      if (e.key === "p") setSelected(items[index - 1]?.id || selected);
    };
    window.addEventListener("keydown", move);
    return () => window.removeEventListener("keydown", move);
  }, [selected, query.data]);
  async function bulk() {
    try {
      await api("/responses/bulk-corrections", {
        method: "POST",
        body: { ids: checked, correction: { is_urgent: false, reason: t("bulkReason") } },
      });
      setChecked([]);
      await client.invalidateQueries({ queryKey: ["feedback"] });
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">{t("title")}</h1>
      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <Input
          aria-label={t("search")}
          placeholder={t("search")}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <select
          aria-label={t("sentiment")}
          className="rounded-lg border p-2"
          value={sentiment}
          onChange={(e) => {
            setSentiment(e.target.value);
            setPage(1);
          }}
        >
          <option value="">{t("allSentiments")}</option>
          {["positive", "negative", "neutral"].map((s) => (
            <option value={s} key={s}>
              {t(`sentiments.${s}` as Parameters<typeof t>[0])}
            </option>
          ))}
        </select>
        <select
          aria-label={t("topics")}
          className="rounded-lg border p-2"
          value={topic}
          onChange={(e) => {
            setTopic(e.target.value);
            setPage(1);
          }}
        >
          <option value="">{t("allTopics")}</option>
          {topics.data?.topics.map((q) => (
            <option key={q.id} value={q.id}>
              {q.name}
            </option>
          ))}
        </select>
        <select
          aria-label={t("channel")}
          className="rounded-lg border p-2"
          value={channel}
          onChange={(e) => {
            setChannel(e.target.value);
            setPage(1);
          }}
        >
          <option value="">{t("allChannels")}</option>
          {["link", "qr", "email", "embed", "kiosk", "import"].map((c) => (
            <option value={c} key={c}>
              {t(`channels.${c}` as Parameters<typeof t>[0])}
            </option>
          ))}
        </select>
        <select
          aria-label={t("sort")}
          className="rounded-lg border p-2"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          {["urgent", "newest", "oldest", "confidence"].map((s) => (
            <option value={s} key={s}>
              {t(`sorts.${s}` as Parameters<typeof t>[0])}
            </option>
          ))}
        </select>
        <label>
          {t("start")}
          <Input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label>
          {t("end")}
          <Input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={urgent}
            onChange={(e) => {
              setUrgent(e.target.checked);
              setPage(1);
            }}
          />
          {t("urgentOnly")}
        </label>
      </div>
      {(error || query.error) && <p role="alert">{error || query.error?.message}</p>}
      {query.isLoading && <p role="status">{t("loading")}</p>}
      {query.data?.total === 0 && <p>{t("empty")}</p>}
      {!!checked.length && canEdit && (
        <Button
          onClick={() => {
            void bulk();
          }}
        >
          {t("bulkClear", { count: checked.length })}
        </Button>
      )}
      <div className="overflow-x-auto rounded-xl border bg-card">
        <table className="w-full text-sm">
          <caption className="sr-only">{t("title")}</caption>
          <thead>
            <tr>
              {["select", "text", "rating", "sentiment", "topics", "channel", "time"].map((key) => (
                <th className="p-3 text-left" key={key}>
                  {t(key as Parameters<typeof t>[0])}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {query.data?.items.map((row) => (
              <tr
                key={row.id}
                className={row.is_urgent ? "bg-orange-50 dark:bg-orange-950/30" : ""}
              >
                <td className="p-3">
                  <input
                    type="checkbox"
                    aria-label={t("selectRow")}
                    checked={checked.includes(row.id)}
                    onChange={(e) =>
                      setChecked(
                        e.target.checked
                          ? [...checked, row.id]
                          : checked.filter((id) => id !== row.id),
                      )
                    }
                  />
                </td>
                <td className="max-w-md p-3">
                  <button
                    className="line-clamp-2 text-left underline"
                    onClick={() => setSelected(row.id)}
                  >
                    {row.is_urgent && "⚠ "}
                    {row.text}
                  </button>
                </td>
                <td className="p-3">{row.rating ?? "—"}</td>
                <td className="p-3">
                  <span
                    className={
                      row.sentiment === "positive"
                        ? "text-green-700"
                        : row.sentiment === "negative"
                          ? "text-red-700"
                          : "text-muted-foreground"
                    }
                  >
                    {row.sentiment
                      ? t(`sentiments.${row.sentiment}` as Parameters<typeof t>[0])
                      : t("pending")}
                  </span>
                  {row.sentiment_score !== null && (
                    <span> {Math.round(row.sentiment_score * 100)}%</span>
                  )}
                </td>
                <td className="p-3">
                  {row.topic_ids
                    .map((id) => topics.data?.topics.find((q) => q.id === id)?.name)
                    .filter(Boolean)
                    .join(", ") || t("unclassified")}
                </td>
                <td className="p-3">{t(`channels.${row.channel}` as Parameters<typeof t>[0])}</td>
                <td className="p-3 whitespace-nowrap">
                  {new Date(row.responded_at).toLocaleString("vi-VN")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          disabled={page === 1}
          onClick={() => {
            setPage(page - 1);
            setChecked([]);
          }}
        >
          {t("previous")}
        </Button>
        <span>{page}</span>
        <Button
          variant="outline"
          disabled={!query.data || page * 20 >= query.data.total}
          onClick={() => {
            setPage(page + 1);
            setChecked([]);
          }}
        >
          {t("next")}
        </Button>
      </div>
      <section className="space-y-3 rounded-xl border p-5">
        <h2 className="text-xl font-semibold">{t("quality")}</h2>
        <p>{t("qualityNote")}</p>
        {quality.data && (
          <p>
            {t("qualityCounts", {
              total: quality.data.total,
              verified: quality.data.verified,
              corrected: quality.data.corrected,
            })}
          </p>
        )}
        {canExport && workspace && (
          <div className="flex gap-3">
            {["csv", "jsonl"].map((format) => (
              <a
                key={format}
                className="underline"
                href={apiUrl(
                  `/model-quality/dataset?workspace_id=${workspace.id}&format=${format}`,
                )}
              >
                {t("dataset", { format: format.toUpperCase() })}
              </a>
            ))}
          </div>
        )}
      </section>
      <Sheet
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <SheetContent className="overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>{t("detail")}</SheetTitle>
          </SheetHeader>
          {selected && (
            <FeedbackDetail key={selected} id={selected} topics={topics.data?.topics || []} />
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function FeedbackDetail({ id, topics }: { id: string; topics: Topic[] }) {
  const t = useTranslations("feedbackManager");
  const query = useQuery({
    queryKey: ["feedback-detail", id],
    queryFn: () => api<Feedback>(`/responses/${id}`),
  });
  if (query.error) return <p role="alert">{query.error.message}</p>;
  if (!query.data) return <p role="status">{t("loading")}</p>;
  return <CorrectionForm key={query.data.updated_at} row={query.data} topics={topics} />;
}

function CorrectionForm({ row, topics }: { row: Feedback; topics: Topic[] }) {
  const t = useTranslations("feedbackManager");
  const client = useQueryClient();
  const canEdit = useCan("label:edit");
  const canApprove = useCan("label:approve");
  const [sentiment, setSentiment] = useState(row.sentiment || "neutral");
  const [selectedTopics, setSelectedTopics] = useState(row.topic_ids);
  const [urgent, setUrgent] = useState(row.is_urgent);
  const [note, setNote] = useState(row.note || "");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const history = useQuery({
    queryKey: ["history", row.id],
    queryFn: () => api<History[]>(`/analyses/${row.id}/corrections`),
  });
  async function perform(path: string, body?: unknown) {
    setBusy(true);
    setError("");
    try {
      await api(path, { method: "POST", body });
      await Promise.all([
        client.invalidateQueries({ queryKey: ["feedback"] }),
        client.invalidateQueries({ queryKey: ["feedback-detail", row.id] }),
        client.invalidateQueries({ queryKey: ["history", row.id] }),
        client.invalidateQueries({ queryKey: ["quality"] }),
      ]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="space-y-4 px-5 pb-5">
      <p className="whitespace-pre-wrap">{row.text}</p>
      <p>{row.urgent_reasons.join(", ")}</p>
      <p>{t("shortcuts")}</p>
      <fieldset disabled={!canEdit || busy} className="space-y-4">
        <label className="block">
          {t("sentiment")}
          <select
            className="block w-full rounded-lg border p-2"
            value={sentiment}
            onChange={(e) => setSentiment(e.target.value)}
          >
            {["positive", "negative", "neutral"].map((s) => (
              <option key={s} value={s}>
                {t(`sentiments.${s}` as Parameters<typeof t>[0])}
              </option>
            ))}
          </select>
        </label>
        <div>
          {topics.map((topic) => (
            <label className="flex gap-2" key={topic.id}>
              <input
                type="checkbox"
                checked={selectedTopics.includes(topic.id)}
                onChange={(e) =>
                  setSelectedTopics(
                    e.target.checked
                      ? [...selectedTopics, topic.id]
                      : selectedTopics.filter((id) => id !== topic.id),
                  )
                }
              />
              {topic.name}
            </label>
          ))}
        </div>
        <label className="flex gap-2">
          <input type="checkbox" checked={urgent} onChange={(e) => setUrgent(e.target.checked)} />
          {t("urgent")}
        </label>
        <label className="block">
          {t("note")}
          <textarea
            className="w-full rounded-lg border p-2"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </label>
        <label className="block">
          {t("reason")}
          <Input value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
        <Button
          onClick={() => {
            void perform(`/analyses/${row.id}/corrections`, {
              sentiment,
              topic_ids: selectedTopics,
              is_urgent: urgent,
              note,
              reason,
              expected_updated_at: row.updated_at,
            });
          }}
        >
          {t("save")}
        </Button>
      </fieldset>
      {error && <p role="alert">{error}</p>}
      <h3 className="font-semibold">{t("history")}</h3>
      {history.data?.map((h) => (
        <div key={h.id} className="space-y-2 rounded-lg border p-3">
          <p>
            {t(`fields.${h.field}` as Parameters<typeof t>[0])}: {JSON.stringify(h.old_value)} →{" "}
            {JSON.stringify(h.new_value)}
          </p>
          <p>{h.reason}</p>
          {!h.reverted_at && canEdit && (
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => {
                void perform(`/corrections/${h.id}/undo`);
              }}
            >
              {t("undo")}
            </Button>
          )}
          {h.review_status === "pending" && canApprove && (
            <Button
              disabled={busy}
              onClick={() => {
                void perform(`/corrections/${h.id}/review?approved=true`);
              }}
            >
              {t("approve")}
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}
