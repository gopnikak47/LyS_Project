"use client";
import { useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api/client";
import { useCan, useCurrentWorkspace } from "@/lib/api/hooks";
import type { Page } from "@/lib/api/surveys";
import { Button } from "@/components/ui/button";

type Ticket = {
  id: string;
  title: string;
  analysis_id: string | null;
  status: string;
  priority: string;
  assignee_id: string | null;
  due_at: string | null;
  notes: { text: string; created_at: string }[];
};
export function TicketsManager() {
  const t = useTranslations("engagement");
  const { workspace } = useCurrentWorkspace();
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["tickets", workspace?.id, status, page],
    enabled: !!workspace,
    queryFn: () =>
      api<Page<Ticket>>(
        `/tickets?workspace_id=${workspace!.id}&page=${page}${status ? `&status=${status}` : ""}`,
      ),
  });
  const assignees = useQuery({
    queryKey: ["assignees", workspace?.id],
    enabled: !!workspace,
    queryFn: () =>
      api<{ id: string; name: string }[]>(`/tickets/assignees?workspace_id=${workspace!.id}`),
  });
  const metrics = useQuery({
    queryKey: ["ticket-metrics", workspace?.id],
    enabled: !!workspace,
    queryFn: () =>
      api<{ average_resolution_seconds: number | null }>(
        `/tickets/metrics?workspace_id=${workspace!.id}`,
      ),
  });
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">{t("tickets")}</h1>
      <p>
        {t("resolution", {
          hours:
            metrics.data?.average_resolution_seconds == null
              ? "—"
              : (metrics.data.average_resolution_seconds / 3600).toFixed(1),
        })}
      </p>
      <select
        aria-label={t("status")}
        className="rounded-lg border p-2"
        value={status}
        onChange={(e) => {
          setStatus(e.target.value);
          setPage(1);
        }}
      >
        <option value="">{t("all")}</option>
        {["new", "in_progress", "done"].map((s) => (
          <option value={s} key={s}>
            {t(`statuses.${s}` as Parameters<typeof t>[0])}
          </option>
        ))}
      </select>
      {query.error && <p role="alert">{query.error.message}</p>}
      {query.data?.total === 0 && <p>{t("empty")}</p>}
      {query.data?.items.map((ticket) => (
        <TicketEditor key={ticket.id} ticket={ticket} assignees={assignees.data || []} />
      ))}
      <div className="flex gap-3">
        <Button variant="outline" disabled={page === 1} onClick={() => setPage(page - 1)}>
          {t("previous")}
        </Button>
        <span>{page}</span>
        <Button
          variant="outline"
          disabled={!query.data || page * 20 >= query.data.total}
          onClick={() => setPage(page + 1)}
        >
          {t("next")}
        </Button>
      </div>
    </div>
  );
}
function TicketEditor({
  ticket,
  assignees,
}: {
  ticket: Ticket;
  assignees: { id: string; name: string }[];
}) {
  const t = useTranslations("engagement"),
    client = useQueryClient();
  const canEdit = useCan("label:edit");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  async function update(fields: unknown) {
    try {
      await api(`/tickets/${ticket.id}`, { method: "PATCH", body: fields });
      setNote("");
      await client.invalidateQueries({ queryKey: ["tickets"] });
      await client.invalidateQueries({ queryKey: ["ticket-metrics"] });
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <article className="space-y-3 rounded-xl border bg-card p-5">
      <h2 className="font-semibold">{ticket.title}</h2>
      <p>{t(`priorities.${ticket.priority}` as Parameters<typeof t>[0])}</p>
      <fieldset disabled={!canEdit} className="flex flex-wrap gap-3">
        <label>
          {t("status")}
          <select
            className="ml-2 rounded border p-2"
            value={ticket.status}
            onChange={(e) => {
              void update({ status: e.target.value });
            }}
          >
            {["new", "in_progress", "done"].map((s) => (
              <option value={s} key={s}>
                {t(`statuses.${s}` as Parameters<typeof t>[0])}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("assignee")}
          <select
            className="ml-2 rounded border p-2"
            value={ticket.assignee_id || ""}
            onChange={(e) => {
              void update({ assignee_id: e.target.value || null });
            }}
          >
            <option value="">{t("unassigned")}</option>
            {assignees.map((a) => (
              <option value={a.id} key={a.id}>
                {a.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          {t("due")}
          <input
            type="datetime-local"
            className="ml-2 rounded border p-2"
            value={
              ticket.due_at
                ? new Date(
                    new Date(ticket.due_at).getTime() - new Date().getTimezoneOffset() * 60000,
                  )
                    .toISOString()
                    .slice(0, 16)
                : ""
            }
            onChange={(e) => {
              void update({
                due_at: e.target.value ? new Date(e.target.value).toISOString() : null,
              });
            }}
          />
        </label>
        <label className="w-full">
          {t("note")}
          <textarea
            className="block w-full rounded border p-2"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </label>
        <Button
          disabled={!note}
          onClick={() => {
            void update({ note });
          }}
        >
          {t("addNote")}
        </Button>
      </fieldset>
      {error && <p role="alert">{error}</p>}
      {ticket.notes.map((n, i) => (
        <p key={i} className="rounded border p-2">
          {n.text} · {new Date(n.created_at).toLocaleString("vi-VN")}
        </p>
      ))}
      <Link href="/responses" className="underline">
        {t("responses")}
      </Link>
    </article>
  );
}
