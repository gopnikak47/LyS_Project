"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useTranslations } from "next-intl";
import { CircleAlert, CircleCheck, Loader2 } from "lucide-react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api/client";
import { usePasswordSchema } from "./auth-form";

function Notice({ tone, children }: { tone: "ok" | "error"; children: React.ReactNode }) {
  const ok = tone === "ok";
  const Icon = ok ? CircleCheck : CircleAlert;
  return (
    <p
      role={ok ? "status" : "alert"}
      className={
        ok
          ? "flex items-start gap-2 rounded-lg bg-positive-soft p-3 text-sm text-positive-ink"
          : "flex items-start gap-2 rounded-lg bg-negative-soft p-3 text-sm text-negative-ink"
      }
    >
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      {children}
    </p>
  );
}

export function ForgotPasswordForm() {
  const t = useTranslations("auth");
  const tv = useTranslations("validation");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const form = useForm<{ email: string }>({
    resolver: standardSchemaResolver(z.object({ email: z.email(tv("email")) })),
    defaultValues: { email: "" },
  });
  const { errors, isSubmitting } = form.formState;

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={form.handleSubmit(async ({ email }) => {
        setError(null);
        try {
          await api("/auth/forgot-password", { method: "POST", body: { email } });
          setSent(true);
        } catch (e) {
          setError(e instanceof ApiError ? e.message : t("forgotSubmit"));
        }
      })}
    >
      <Field data-invalid={!!errors.email}>
        <FieldLabel htmlFor="email">{t("email")}</FieldLabel>
        <Input id="email" type="email" autoComplete="email" {...form.register("email")} />
        <FieldError errors={[errors.email]} />
      </Field>
      {sent && <Notice tone="ok">{t("forgotSent")}</Notice>}
      {error && <Notice tone="error">{error}</Notice>}
      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
        {t("forgotSubmit")}
      </Button>
      <p className="text-center text-sm">
        <Link href="/login" className="text-primary hover:underline">
          {t("backToLogin")}
        </Link>
      </p>
    </form>
  );
}

export function ResetPasswordForm() {
  const t = useTranslations("auth");
  const router = useRouter();
  const token = useSearchParams().get("token");
  const [error, setError] = useState<string | null>(null);
  const passwordSchema = usePasswordSchema();
  const form = useForm<{ password: string; confirm: string }>({
    resolver: standardSchemaResolver(
      z
        .object({ password: passwordSchema, confirm: z.string() })
        .refine((v) => v.password === v.confirm, {
          message: t("passwordMismatch"),
          path: ["confirm"],
        }),
    ),
    defaultValues: { password: "", confirm: "" },
  });
  const { errors, isSubmitting } = form.formState;

  if (!token) return <Notice tone="error">{t("missingToken")}</Notice>;

  return (
    <form
      noValidate
      className="space-y-5"
      onSubmit={form.handleSubmit(async ({ password }) => {
        setError(null);
        try {
          await api("/auth/reset-password", { method: "POST", body: { token, password } });
          router.replace("/login?reset=1");
        } catch (e) {
          setError(e instanceof ApiError ? e.message : t("resetSubmit"));
        }
      })}
    >
      <FieldGroup className="gap-5">
        <Field data-invalid={!!errors.password}>
          <FieldLabel htmlFor="password">{t("newPassword")}</FieldLabel>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            {...form.register("password")}
          />
          {!errors.password && <FieldDescription>{t("passwordHint")}</FieldDescription>}
          <FieldError errors={[errors.password]} />
        </Field>
        <Field data-invalid={!!errors.confirm}>
          <FieldLabel htmlFor="confirm">{t("confirmPassword")}</FieldLabel>
          <Input
            id="confirm"
            type="password"
            autoComplete="new-password"
            {...form.register("confirm")}
          />
          <FieldError errors={[errors.confirm]} />
        </Field>
      </FieldGroup>
      {error && <Notice tone="error">{error}</Notice>}
      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
        {t("resetSubmit")}
      </Button>
    </form>
  );
}

export { Notice };
