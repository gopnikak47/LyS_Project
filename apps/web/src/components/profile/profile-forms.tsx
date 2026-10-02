"use client";

import { useRouter } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";
import { LOCALES } from "@lys/shared";
import { usePasswordSchema } from "@/components/auth/auth-form";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { setLocale } from "@/i18n/actions";
import { api, ApiError } from "@/lib/api/client";
import { queryKeys, useSession } from "@/lib/api/hooks";
import type { Session } from "@/lib/api/types";

export function ProfileForms() {
  const t = useTranslations("profile");
  const tc = useTranslations("common");
  const ta = useTranslations("auth");
  const tr = useTranslations("roles");
  const tv = useTranslations("validation");
  const router = useRouter();
  const client = useQueryClient();
  const { data: session } = useSession();
  const passwordSchema = usePasswordSchema();

  const info = useForm<{ fullName: string; locale: "vi" | "en" }>({
    resolver: standardSchemaResolver(
      z.object({
        fullName: z
          .string()
          .trim()
          .min(2, tv("minLength", { min: 2 })),
        locale: z.enum(LOCALES),
      }),
    ),
    values: {
      fullName: session?.user.full_name ?? "",
      locale: (session?.user.locale as "vi" | "en") ?? "vi",
    },
  });
  const saveInfo = useMutation({
    mutationFn: (v: { fullName: string; locale: "vi" | "en" }) =>
      api("/auth/me", { method: "PATCH", body: { full_name: v.fullName, locale: v.locale } }),
    onSuccess: async (_, v) => {
      toast.success(tc("saved"));
      await client.invalidateQueries({ queryKey: queryKeys.session });
      // Đồng bộ ngôn ngữ giao diện với lựa chọn trong hồ sơ.
      await setLocale(v.locale);
      router.refresh();
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : tc("errorGeneric")),
  });

  const pw = useForm<{ current: string; next: string; confirm: string }>({
    resolver: standardSchemaResolver(
      z
        .object({
          current: z.string().min(1, tv("required")),
          next: passwordSchema,
          confirm: z.string(),
        })
        .refine((v) => v.next === v.confirm, {
          message: ta("passwordMismatch"),
          path: ["confirm"],
        }),
    ),
    defaultValues: { current: "", next: "", confirm: "" },
  });
  const changePassword = useMutation({
    mutationFn: (v: { current: string; next: string }) =>
      api<Session>("/auth/change-password", {
        method: "POST",
        body: { current_password: v.current, new_password: v.next },
      }),
    onSuccess: (session) => {
      toast.success(t("passwordChanged"));
      client.setQueryData(queryKeys.session, session);
      pw.reset();
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 401) {
        pw.setError("current", { message: e.message });
      } else toast.error(e instanceof ApiError ? e.message : tc("errorGeneric"));
    },
  });

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>{t("info")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            noValidate
            className="space-y-5"
            onSubmit={info.handleSubmit((v) => saveInfo.mutate(v))}
          >
            <FieldGroup className="gap-4">
              <Field data-invalid={!!info.formState.errors.fullName}>
                <FieldLabel htmlFor="profile-name">{t("fullName")}</FieldLabel>
                <Input id="profile-name" autoComplete="name" {...info.register("fullName")} />
                <FieldError errors={[info.formState.errors.fullName]} />
              </Field>
              <Field>
                <FieldLabel htmlFor="profile-email">{t("email")}</FieldLabel>
                <Input id="profile-email" value={session?.user.email ?? ""} readOnly disabled />
              </Field>
              <Field>
                <FieldLabel htmlFor="profile-locale">{t("language")}</FieldLabel>
                <Controller
                  control={info.control}
                  name="locale"
                  render={({ field }) => (
                    <Select value={field.value} onValueChange={field.onChange}>
                      <SelectTrigger id="profile-locale" className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {LOCALES.map((l) => (
                          <SelectItem key={l} value={l}>
                            {tc(`languages.${l}`)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                />
              </Field>
            </FieldGroup>
            <Button type="submit" disabled={saveInfo.isPending}>
              {saveInfo.isPending && <Loader2 className="animate-spin" aria-hidden />}
              {tc("save")}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t("security")}</CardTitle>
        </CardHeader>
        <CardContent>
          <form
            noValidate
            className="space-y-5"
            onSubmit={pw.handleSubmit((v) => changePassword.mutate(v))}
          >
            <FieldGroup className="gap-4">
              {(["current", "next", "confirm"] as const).map((name) => (
                <Field key={name} data-invalid={!!pw.formState.errors[name]}>
                  <FieldLabel htmlFor={`pw-${name}`}>
                    {name === "current"
                      ? t("currentPassword")
                      : name === "next"
                        ? ta("newPassword")
                        : ta("confirmPassword")}
                  </FieldLabel>
                  <Input
                    id={`pw-${name}`}
                    type="password"
                    autoComplete={name === "current" ? "current-password" : "new-password"}
                    {...pw.register(name)}
                  />
                  {name === "next" && !pw.formState.errors.next && (
                    <FieldDescription>{ta("passwordHint")}</FieldDescription>
                  )}
                  <FieldError errors={[pw.formState.errors[name]]} />
                </Field>
              ))}
            </FieldGroup>
            <Button type="submit" disabled={changePassword.isPending}>
              {changePassword.isPending && <Loader2 className="animate-spin" aria-hidden />}
              {t("changePassword")}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>{t("memberships")}</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="divide-y">
            {session?.memberships.map((m) => (
              <li key={m.tenant_id} className="flex items-center justify-between gap-3 py-3">
                <span className="font-medium">{m.tenant_name}</span>
                <Badge variant={m.tenant_id === session.tenant.id ? "default" : "outline"}>
                  {tr(m.role)}
                </Badge>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
