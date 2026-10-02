"use client";

import { useState } from "react";
import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { restrictToVerticalAxis } from "@dnd-kit/modifiers";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  Combine,
  GripVertical,
  LayoutTemplate,
  Pencil,
  Plus,
  RefreshCw,
  Tags,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { EmptyState, ErrorState } from "@/components/feedback/states";
import { PageHeader } from "@/components/layout/page-header";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { api, ApiError } from "@/lib/api/client";
import { useCan, useCurrentWorkspace } from "@/lib/api/hooks";
import type { Topic, TopicSet } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { MergeDialog, TemplateDialog, TopicDialog, type TopicPayload } from "./topic-dialogs";

function SortableTopic({
  topic,
  canManage,
  selected,
  onSelect,
  onEdit,
  onToggle,
  onDelete,
}: {
  topic: Topic;
  canManage: boolean;
  selected: boolean;
  onSelect: (checked: boolean) => void;
  onEdit: () => void;
  onToggle: (active: boolean) => void;
  onDelete: () => void;
}) {
  const t = useTranslations("topics");
  const tc = useTranslations("common");
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: topic.id,
    disabled: !canManage,
  });

  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn(
        "flex items-start gap-3 rounded-xl border bg-card p-4 shadow-soft",
        isDragging && "relative z-10 ring-2 ring-primary/40",
        !topic.is_active && "opacity-70",
      )}
    >
      {canManage && (
        <>
          <button
            type="button"
            className="mt-0.5 cursor-grab touch-none rounded-md p-1 text-muted-foreground hover:bg-accent focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none active:cursor-grabbing"
            aria-label={t("dragHandle", { name: topic.name })}
            {...attributes}
            {...listeners}
          >
            <GripVertical className="size-4" aria-hidden />
          </button>
          <Checkbox
            className="mt-1.5"
            checked={selected}
            onCheckedChange={(c) => onSelect(c === true)}
            aria-label={t("select", { name: topic.name })}
          />
        </>
      )}
      <span
        aria-hidden
        className="mt-1.5 size-3 shrink-0 rounded-full"
        style={{ backgroundColor: topic.color }}
      />
      <div className="min-w-0 flex-1 space-y-1.5">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold">{topic.name}</h3>
          <Badge variant={topic.is_active ? "positive" : "neutral"}>
            {topic.is_active ? t("active") : t("inactive")}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {t("usage", { count: topic.usage_count })}
          </span>
        </div>
        {topic.description && <p className="text-sm text-muted-foreground">{topic.description}</p>}
        {topic.keywords.length > 0 && (
          <ul className="flex flex-wrap gap-1">
            {topic.keywords.map((k) => (
              <li
                key={k}
                className="rounded-md bg-muted px-1.5 py-0.5 text-xs text-muted-foreground"
              >
                {k}
              </li>
            ))}
          </ul>
        )}
      </div>
      {canManage && (
        <div className="flex shrink-0 items-center gap-1">
          <Switch
            checked={topic.is_active}
            onCheckedChange={onToggle}
            aria-label={topic.is_active ? t("active") : t("inactive")}
          />
          <Button variant="ghost" size="icon-sm" onClick={onEdit} aria-label={tc("edit")}>
            <Pencil aria-hidden />
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label={tc("delete")}>
                <Trash2 aria-hidden />
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{t("deleteTitle", { name: topic.name })}</AlertDialogTitle>
                <AlertDialogDescription>
                  {t("deleteDescription", { count: topic.usage_count })}
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
                <AlertDialogAction
                  className="bg-destructive text-white hover:bg-destructive/90"
                  onClick={onDelete}
                >
                  {tc("delete")}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      )}
    </li>
  );
}

export function TopicsManager() {
  const t = useTranslations("topics");
  const tc = useTranslations("common");
  const ts = useTranslations("states");
  const canManage = useCan("topic:manage");
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();
  const client = useQueryClient();
  const key = ["topics", workspace?.id];
  const query = useQuery({
    queryKey: key,
    queryFn: () => api<TopicSet>(`/workspaces/${workspace!.id}/topics`),
    enabled: !!workspace,
  });
  const [editing, setEditing] = useState<Topic | null>(null);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [merging, setMerging] = useState(false);
  const [templating, setTemplating] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const onError = (e: unknown) =>
    toast.error(e instanceof ApiError ? e.message : tc("errorGeneric"));
  const refresh = () => client.invalidateQueries({ queryKey: key });

  const save = useMutation({
    mutationFn: (payload: TopicPayload) =>
      editing
        ? api<Topic>(`/topics/${editing.id}`, { method: "PATCH", body: payload })
        : api<Topic>(`/workspaces/${workspace!.id}/topics`, { method: "POST", body: payload }),
    onSuccess: () => {
      toast.success(editing ? tc("saved") : t("created"));
      setEditing(null);
      setCreating(false);
      refresh();
    },
    onError,
  });
  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      api(`/topics/${id}`, { method: "PATCH", body: { is_active: active } }),
    onSuccess: refresh,
    onError,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/topics/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success(t("deleted"));
      refresh();
    },
    onError,
  });
  const reorder = useMutation({
    mutationFn: (ids: string[]) =>
      api(`/workspaces/${workspace!.id}/topics/order`, { method: "PUT", body: { ids } }),
    onSuccess: () => toast.success(t("reordered")),
    onError: (e) => {
      onError(e);
      refresh();
    },
  });
  const merge = useMutation({
    mutationFn: (target: string) =>
      api(`/workspaces/${workspace!.id}/topics/merge`, {
        method: "POST",
        body: { source_ids: selected, target_id: target },
      }),
    onSuccess: () => {
      toast.success(t("merged"));
      setSelected([]);
      setMerging(false);
      refresh();
    },
    onError,
  });
  const reanalyze = useMutation({
    mutationFn: () =>
      api<{ pending: number }>(`/workspaces/${workspace!.id}/topics/reanalyze`, { method: "POST" }),
    onSuccess: (data) => toast.success(t("reanalyzeQueued", { count: data.pending })),
    onError,
  });

  function onDragEnd(event: DragEndEvent) {
    const topics = query.data?.topics ?? [];
    if (!event.over || event.active.id === event.over.id) return;
    const from = topics.findIndex((x) => x.id === event.active.id);
    const to = topics.findIndex((x) => x.id === event.over!.id);
    const next = arrayMove(topics, from, to);
    client.setQueryData<TopicSet>(key, (old) => (old ? { ...old, topics: next } : old));
    reorder.mutate(next.map((x) => x.id));
  }

  if (!wsLoading && !workspace) return <EmptyState title={t("noWorkspace")} />;
  const topics = query.data?.topics ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("title")}
        description={workspace ? t("subtitle", { workspace: workspace.name }) : undefined}
        actions={
          canManage && (
            <>
              <Button variant="outline" onClick={() => setTemplating(true)}>
                <LayoutTemplate aria-hidden />
                {t("template")}
              </Button>
              <Button onClick={() => setCreating(true)}>
                <Plus aria-hidden />
                {t("add")}
              </Button>
            </>
          )
        }
      />

      {canManage && (
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={selected.length < 1 || topics.length < 2}
            onClick={() => setMerging(true)}
          >
            <Combine aria-hidden />
            {t("mergeSelected", { count: selected.length })}
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="ghost" size="sm" disabled={reanalyze.isPending}>
                <RefreshCw aria-hidden className={cn(reanalyze.isPending && "animate-spin")} />
                {t("reanalyze")}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{t("reanalyzeTitle")}</AlertDialogTitle>
                <AlertDialogDescription>{t("reanalyzeDescription")}</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>{tc("cancel")}</AlertDialogCancel>
                <AlertDialogAction onClick={() => reanalyze.mutate()}>
                  {tc("confirm")}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
          {query.data && (
            <span className="ml-auto text-xs text-muted-foreground">
              {t("version", { version: query.data.version })}
            </span>
          )}
        </div>
      )}

      {query.isLoading || wsLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      ) : query.error ? (
        <ErrorState
          title={ts("errorTitle")}
          description={ts("errorDescription")}
          action={
            <Button variant="outline" size="sm" onClick={() => query.refetch()}>
              {tc("retry")}
            </Button>
          }
        />
      ) : topics.length === 0 ? (
        <EmptyState icon={Tags} title={t("emptyTitle")} description={t("emptyDescription")} />
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          modifiers={[restrictToVerticalAxis]}
          onDragEnd={onDragEnd}
        >
          <SortableContext items={topics.map((x) => x.id)} strategy={verticalListSortingStrategy}>
            <ul className="space-y-3">
              {topics.map((topic) => (
                <SortableTopic
                  key={topic.id}
                  topic={topic}
                  canManage={canManage}
                  selected={selected.includes(topic.id)}
                  onSelect={(c) =>
                    setSelected((s) => (c ? [...s, topic.id] : s.filter((id) => id !== topic.id)))
                  }
                  onEdit={() => setEditing(topic)}
                  onToggle={(active) => toggle.mutate({ id: topic.id, active })}
                  onDelete={() => remove.mutate(topic.id)}
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>
      )}

      <TopicDialog
        topic={editing}
        open={creating || !!editing}
        onOpenChange={(open) => {
          if (!open) {
            setCreating(false);
            setEditing(null);
          }
        }}
        onSubmit={(payload) => save.mutate(payload)}
        pending={save.isPending}
      />
      <MergeDialog
        sources={topics.filter((x) => selected.includes(x.id))}
        candidates={topics}
        open={merging}
        onOpenChange={setMerging}
        onMerge={(target) => merge.mutate(target)}
        pending={merge.isPending}
      />
      <TemplateDialog
        open={templating}
        onOpenChange={setTemplating}
        onApply={async (code, replace) => {
          try {
            await api(`/workspaces/${workspace!.id}/topics/apply-template`, {
              method: "POST",
              body: { template_code: code, replace },
            });
            toast.success(t("templateApplied"));
            setSelected([]);
            refresh();
          } catch (e) {
            onError(e);
            throw e;
          }
        }}
      />
    </div>
  );
}
