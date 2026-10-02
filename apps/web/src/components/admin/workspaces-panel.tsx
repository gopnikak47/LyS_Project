"use client";

import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";
import { INDUSTRIES } from "@lys/shared";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api/client";
import { queryKeys, useWorkspaces } from "@/lib/api/hooks";
import type { Workspace } from "@/lib/api/types";

type Values = { name: string; description?: string; industry?: string; color: string };

function WorkspaceDialog({
  workspace,
  open,
  onOpenChange,
}: {
  workspace: Workspace | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const t = useTranslations("admin.workspaces");
  const tc = useTranslations("common");
  const tv = useTranslations("validation");
  const tk = useTranslations("uiKit.industries");
  const ta = useTranslations("auth");
  const client = useQueryClient();
  const form = useForm<Values>({
    resolver: standardSchemaResolver(
      z.object({
        name: z
          .string()
          .trim()
          .min(2, tv("minLength", { min: 2 }))
          .max(200),
        description: z.string().max(1000).optional(),
        industry: z.string().optional(),
        color: z.string().regex(/^#[0-9a-fA-F]{6}$/),
      }),
    ),
    values: {
      name: workspace?.name ?? "",
      description: workspace?.description ?? "",
      industry: workspace?.industry ?? "",
      color: workspace?.color ?? "#4f46e5",
    },
  });
  const save = useMutation({
    mutationFn: (values: Values) => {
      const body = { ...values, industry: values.industry || null };
      return workspace
        ? api<Workspace>(`/workspaces/${workspace.id}`, { method: "PATCH", body })
        : api<Workspace>("/workspaces", { method: "POST", body });
    },
    onSuccess: () => {
      toast.success(workspace ? tc("saved") : t("created"));
      client.invalidateQueries({ queryKey: queryKeys.workspaces });
      onOpenChange(false);
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : tc("errorGeneric")),
  });
  const { errors } = form.formState;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{workspace ? t("edit") : t("create")}</DialogTitle>
          <DialogDescription className="sr-only">{t("namePlaceholder")}</DialogDescription>
        </DialogHeader>
        <form id="workspace-form" noValidate onSubmit={form.handleSubmit((v) => save.mutate(v))}>
          <FieldGroup className="gap-4">
            <Field data-invalid={!!errors.name}>
              <FieldLabel htmlFor="ws-name">{t("name")}</FieldLabel>
              <Input id="ws-name" placeholder={t("namePlaceholder")} {...form.register("name")} />
              <FieldError errors={[errors.name]} />
            </Field>
            <Field>
              <FieldLabel htmlFor="ws-description">{t("description")}</FieldLabel>
              <Textarea id="ws-description" rows={2} {...form.register("description")} />
            </Field>
            {!workspace && (
              <Field>
                <FieldLabel htmlFor="ws-industry">{ta("industry")}</FieldLabel>
                <Controller
                  control={form.control}
                  name="industry"
                  render={({ field }) => (
                    <Select value={field.value || undefined} onValueChange={field.onChange}>
                      <SelectTrigger id="ws-industry" className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {INDUSTRIES.map((industry) => (
                          <SelectItem key={industry} value={industry}>
                            {tk(industry)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </Field>
            )}
            <Field orientation="horizontal">
              <input
                id="ws-color"
                type="color"
                className="h-9 w-12 cursor-pointer rounded-md border"
                {...form.register("color")}
              />
              <FieldLabel htmlFor="ws-color" className="font-normal">
                {t("color")}
              </FieldLabel>
            </Field>
          </FieldGroup>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {tc("cancel")}
          </Button>
          <Button type="submit" form="workspace-form" disabled={save.isPending}>
            {save.isPending && <Loader2 className="animate-spin" aria-hidden />}
            {tc("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DeleteWorkspaceDialog({
  workspace,
  onClose,
}: {
  workspace: Workspace | null;
  onClose: () => void;
}) {
  const t = useTranslations("admin.workspaces");
  const tc = useTranslations("common");
  const client = useQueryClient();
  const [confirm, setConfirm] = useState("");
  const remove = useMutation({
    mutationFn: () =>
      api(`/workspaces/${workspace!.id}/delete`, {
        method: "POST",
        body: { confirm_name: confirm },
      }),
    onSuccess: () => {
      toast.success(t("deleted"));
      client.invalidateQueries({ queryKey: queryKeys.workspaces });
      onClose();
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : tc("errorGeneric")),
  });

  return (
    <Dialog
      open={!!workspace}
      onOpenChange={(open) => {
        if (!open) {
          setConfirm("");
          onClose();
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("deleteTitle", { name: workspace?.name ?? "" })}</DialogTitle>
          <DialogDescription>{t("deleteDescription")}</DialogDescription>
        </DialogHeader>
        <Field>
          <FieldLabel htmlFor="ws-confirm">
            {t("deleteConfirmLabel", { name: workspace?.name ?? "" })}
          </FieldLabel>
          <Input
            id="ws-confirm"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="off"
          />
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {tc("cancel")}
          </Button>
          <Button
            variant="destructive"
            disabled={confirm.trim() !== workspace?.name || remove.isPending}
            onClick={() => remove.mutate()}
          >
            {remove.isPending && <Loader2 className="animate-spin" aria-hidden />}
            {t("delete")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function WorkspacesPanel() {
  const t = useTranslations("admin.workspaces");
  const tk = useTranslations("uiKit.industries");
  const { data: workspaces, isLoading } = useWorkspaces();
  const [editing, setEditing] = useState<Workspace | null>(null);
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<Workspace | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <Button onClick={() => setCreating(true)}>
          <Plus aria-hidden />
          {t("create")}
        </Button>
      </div>
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {workspaces?.map((ws) => (
            <li key={ws.id}>
              <Card className="h-full gap-3 p-5">
                <div className="flex items-start gap-3">
                  <span
                    aria-hidden
                    className="mt-1 size-3 shrink-0 rounded-full"
                    style={{ backgroundColor: ws.color }}
                  />
                  <div className="min-w-0 flex-1">
                    <h3 className="truncate font-semibold">{ws.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {ws.industry ? tk(ws.industry) : "—"} ·{" "}
                      {t("surveys", { count: ws.survey_count })}
                    </p>
                  </div>
                </div>
                {ws.description && (
                  <p className="line-clamp-2 text-sm text-muted-foreground">{ws.description}</p>
                )}
                <div className="mt-auto flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setEditing(ws)}>
                    <Pencil aria-hidden />
                    {t("rename")}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setDeleting(ws)}>
                    <Trash2 aria-hidden />
                    {t("delete")}
                  </Button>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
      <WorkspaceDialog
        workspace={editing}
        open={creating || !!editing}
        onOpenChange={(open) => {
          if (!open) {
            setCreating(false);
            setEditing(null);
          }
        }}
      />
      <DeleteWorkspaceDialog workspace={deleting} onClose={() => setDeleting(null)} />
    </div>
  );
}
