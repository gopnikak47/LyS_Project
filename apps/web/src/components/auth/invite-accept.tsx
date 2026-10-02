"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { Loader2, MailOpen } from "lucide-react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/hooks";
import type { PublicInvitation, Session } from "@/lib/api/types";
import { usePasswordSchema } from "./auth-form";
import { Notice } from "./password-forms";

export function InviteAccept({ token }: { token: string }) {
  const t = useTranslations("auth");
  const tr = useTranslations("roles");
  const tv = useTranslations("validation");
  const ti = useTranslations("admin.invite");
  const format = useFormatter();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const passwordSchema = usePasswordSchema();

  const invite = useQuery({
    queryKey: ["invitation", token],
    queryFn: () => api<PublicInvitation>(`/public/invitations/${encodeURIComponent(token)}`),
    retry: false,
  });

  const existing = invite.data?.user_exists ?? false;
  const schema = existing
    ? z.object({ fullName: z.string().optional(), password: z.string().min(1, tv("required")) })
    : z.object({
        fullName: z
          .string()
          .trim()
          .min(2, tv("minLength", { min: 2 })),
        password: passwordSchema,
      });
  const form = useForm<{ fullName?: string; password: string }>({
    resolver: standardSchemaResolver(schema),
    defaultValues: { fullName: "", password: "" },
  });
  const { errors, isSubmitting } = form.formState;

  if (invite.isLoading) {
    return (
      <Card className="gap-4 p-6" aria-busy="true">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-10 w-full" />
      </Card>
    );
  }
  if (invite.error || !invite.data) {
    return <Notice tone="error">{t("inviteInvalid")}</Notice>;
  }
  const info = invite.data;
  const role = tr(info.role);

  return (
    <Card className="p-2 sm:p-4">
      <CardHeader>
        <span className="mb-2 grid size-11 place-items-center rounded-xl bg-primary-soft text-primary">
          <MailOpen className="size-5" aria-hidden />
        </span>
        <CardTitle className="text-2xl">
          <h1>{t("inviteTitle")}</h1>
        </CardTitle>
        <CardDescription>
          {info.inviter_name
            ? t("inviteSubtitle", { inviter: info.inviter_name, tenant: info.tenant_name, role })
            : t("inviteSubtitleNoInviter", { tenant: info.tenant_name, role })}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          noValidate
          className="space-y-5"
          onSubmit={form.handleSubmit(async (values) => {
            setError(null);
            try {
              const session = await api<Session>(
                `/public/invitations/${encodeURIComponent(token)}/accept`,
                {
                  method: "POST",
                  body: { full_name: values.fullName || null, password: values.password },
                },
              );
              queryClient.setQueryData(queryKeys.session, session);
              router.replace("/surveys");
            } catch (e) {
              setError(e instanceof ApiError ? e.message : t("inviteInvalid"));
            }
          })}
        >
          <p className="text-sm text-muted-foreground">
            {existing
              ? t("inviteExisting", { email: info.email })
              : t("inviteNew", { email: info.email })}
          </p>
          <FieldGroup className="gap-5">
            {!existing && (
              <Field data-invalid={!!errors.fullName}>
                <FieldLabel htmlFor="fullName">{t("fullName")}</FieldLabel>
                <Input id="fullName" autoComplete="name" {...form.register("fullName")} />
                <FieldError errors={[errors.fullName]} />
              </Field>
            )}
            <Field data-invalid={!!errors.password}>
              <FieldLabel htmlFor="password">{t("password")}</FieldLabel>
              <Input
                id="password"
                type="password"
                autoComplete={existing ? "current-password" : "new-password"}
                {...form.register("password")}
              />
              {!existing && !errors.password && (
                <FieldDescription>{t("passwordHint")}</FieldDescription>
              )}
              <FieldError errors={[errors.password]} />
            </Field>
          </FieldGroup>
          <p className="text-xs text-muted-foreground">
            {ti("expires", {
              date: format.dateTime(new Date(info.expires_at), { dateStyle: "medium" }),
            })}
          </p>
          {error && <Notice tone="error">{error}</Notice>}
          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
            {t("inviteAccept")}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
