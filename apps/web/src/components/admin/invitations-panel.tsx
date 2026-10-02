"use client";

import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { Copy, Loader2, MailPlus, X } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";
import { EmptyState } from "@/components/feedback/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/hooks";
import type { Invitation, InvitationCreated } from "@/lib/api/types";
import { WorkspaceScopePicker } from "./workspace-scope";

type FormValues = { email: string; role: "ADMIN" | "ANALYST" | "VIEWER" };

export function InvitationsPanel() {
  const t = useTranslations("admin.invite");
  const tr = useTranslations("roles");
  const tc = useTranslations("common");
  const tv = useTranslations("validation");
  const format = useFormatter();
  const client = useQueryClient();
  const [scope, setScope] = useState({ all_workspaces: true, workspace_ids: [] as string[] });
  const [lastLink, setLastLink] = useState<string | null>(null);

  const pending = useQuery({
    queryKey: queryKeys.invitations,
    queryFn: () => api<Invitation[]>("/invitations"),
  });
  const form = useForm<FormValues>({
    resolver: standardSchemaResolver(
      z.object({ email: z.email(tv("email")), role: z.enum(["ADMIN", "ANALYST", "VIEWER"]) }),
    ),
    defaultValues: { email: "", role: "ANALYST" },
  });

  const invite = useMutation({
    mutationFn: (values: FormValues) =>
      api<InvitationCreated>("/invitations", {
        method: "POST",
        body: {
          ...values,
          workspace_ids: scope.all_workspaces ? [] : scope.workspace_ids,
        },
      }),
    onSuccess: (data) => {
      toast.success(t("sent", { email: data.email }));
      setLastLink(data.invite_url);
      form.reset({ email: "", role: form.getValues("role") });
      client.invalidateQueries({ queryKey: queryKeys.invitations });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : tc("errorGeneric")),
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api(`/invitations/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      toast.success(t("revoked"));
      client.invalidateQueries({ queryKey: queryKeys.invitations });
    },
  });
  const { errors } = form.formState;
  const role = useWatch({ control: form.control, name: "role" });

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,26rem)_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            noValidate
            className="space-y-4"
            onSubmit={form.handleSubmit((values) => invite.mutate(values))}
          >
            <Field data-invalid={!!errors.email}>
              <FieldLabel htmlFor="invite-email">{t("email")}</FieldLabel>
              <Input id="invite-email" type="email" {...form.register("email")} />
              <FieldError errors={[errors.email]} />
            </Field>
            <Field>
              <FieldLabel htmlFor="invite-role">{t("role")}</FieldLabel>
              <Controller
                control={form.control}
                name="role"
                render={({ field }) => (
                  <Select value={field.value} onValueChange={field.onChange}>
                    <SelectTrigger id="invite-role" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {(["ADMIN", "ANALYST", "VIEWER"] as const).map((role) => (
                        <SelectItem key={role} value={role}>
                          {tr(role)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              />
            </Field>
            {role !== "ADMIN" && <WorkspaceScopePicker value={scope} onChange={setScope} />}
            <Button type="submit" disabled={invite.isPending} className="w-full">
              {invite.isPending ? (
                <Loader2 className="animate-spin" aria-hidden />
              ) : (
                <MailPlus aria-hidden />
              )}
              {t("submit")}
            </Button>
            {lastLink && (
              <div className="space-y-2 rounded-lg bg-primary-soft p-3 text-sm">
                <p className="text-primary">{t("linkHint")}</p>
                <div className="flex gap-2">
                  <Input
                    readOnly
                    value={lastLink}
                    className="bg-card text-xs"
                    aria-label={t("linkHint")}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    aria-label={tc("copy")}
                    onClick={async () => {
                      await navigator.clipboard.writeText(lastLink);
                      toast.success(tc("copied"));
                    }}
                  >
                    <Copy aria-hidden />
                  </Button>
                </div>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      <section aria-labelledby="pending-invites" className="space-y-3">
        <h2 id="pending-invites" className="font-semibold">
          {t("pending")}
        </h2>
        {pending.isLoading ? (
          <Skeleton className="h-24 w-full rounded-xl" />
        ) : !pending.data?.length ? (
          <EmptyState title={t("none")} />
        ) : (
          <ul className="divide-y rounded-xl border bg-card">
            {pending.data.map((inv) => (
              <li key={inv.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{inv.email}</p>
                  <p className="text-xs text-muted-foreground">
                    {tr(inv.role)} ·{" "}
                    {t("expires", {
                      date: format.dateTime(new Date(inv.expires_at), { dateStyle: "medium" }),
                    })}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => revoke.mutate(inv.id)}
                  disabled={revoke.isPending}
                >
                  <X aria-hidden />
                  {t("revoke")}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
