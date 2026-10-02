"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Controller, useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { CircleAlert, Loader2 } from "lucide-react";
import { z } from "zod";
import { INDUSTRIES } from "@lys/shared";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api/client";
import { queryKeys } from "@/lib/api/hooks";
import type { Session } from "@/lib/api/types";

type Mode = "login" | "register";
type Values = {
  email: string;
  password: string;
  companyName?: string;
  fullName?: string;
  industry?: string;
};

/** Chỉ cho phép chuyển hướng nội bộ (chống open redirect qua ?next=). */
export function safeNext(next: string | null): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/surveys";
}

export function usePasswordSchema() {
  const tv = useTranslations("validation");
  const ta = useTranslations("auth");
  return z
    .string()
    .min(8, tv("minLength", { min: 8 }))
    .max(128, tv("maxLength", { max: 128 }))
    .refine((v) => /\p{L}/u.test(v) && /\d/.test(v), ta("passwordHint"));
}

export function AuthForm({ mode }: { mode: Mode }) {
  const t = useTranslations("auth");
  const tc = useTranslations("common");
  const tv = useTranslations("validation");
  const tk = useTranslations("uiKit.industries");
  const router = useRouter();
  const params = useSearchParams();
  const queryClient = useQueryClient();
  const [formError, setFormError] = useState<string | null>(null);
  const passwordSchema = usePasswordSchema();

  const schema =
    mode === "register"
      ? z.object({
          email: z.email(tv("email")),
          password: passwordSchema,
          companyName: z
            .string()
            .trim()
            .min(2, tv("minLength", { min: 2 })),
          fullName: z
            .string()
            .trim()
            .min(2, tv("minLength", { min: 2 })),
          industry: z.string().optional(),
        })
      : z.object({
          email: z.email(tv("email")),
          password: z.string().min(1, tv("required")),
        });

  const form = useForm<Values>({
    resolver: standardSchemaResolver(schema),
    defaultValues: { email: "", password: "", companyName: "", fullName: "", industry: "" },
  });
  const { errors, isSubmitting } = form.formState;

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const session =
        mode === "register"
          ? await api<Session>("/auth/register", {
              method: "POST",
              body: {
                company_name: values.companyName,
                full_name: values.fullName,
                email: values.email,
                password: values.password,
                industry: values.industry || null,
              },
            })
          : await api<Session>("/auth/login", {
              method: "POST",
              body: { email: values.email, password: values.password },
            });
      queryClient.setQueryData(queryKeys.session, session);
      router.replace(safeNext(params.get("next")));
    } catch (error) {
      if (error instanceof ApiError) {
        const fields = error.fieldErrors();
        const map: Record<string, keyof Values> = {
          company_name: "companyName",
          full_name: "fullName",
          email: "email",
          password: "password",
        };
        Object.entries(fields).forEach(([field, message]) => {
          if (map[field]) form.setError(map[field], { message });
        });
        setFormError(error.message);
      } else {
        setFormError(tc("errorGeneric"));
      }
    }
  }

  const fields: {
    name: "companyName" | "fullName" | "email" | "password";
    type: string;
    auto: string;
  }[] = [
    ...(mode === "register"
      ? [
          { name: "companyName" as const, type: "text", auto: "organization" },
          { name: "fullName" as const, type: "text", auto: "name" },
        ]
      : []),
    { name: "email", type: "email", auto: "email" },
    {
      name: "password",
      type: "password",
      auto: mode === "login" ? "current-password" : "new-password",
    },
  ];

  const ta = useTranslations("app");
  const notice =
    mode === "login" && params.get("reset")
      ? t("resetDone")
      : mode === "login" && params.get("expired")
        ? ta("sessionExpired")
        : null;

  return (
    <form noValidate onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      {notice && (
        <p
          role="status"
          className="flex items-start gap-2 rounded-lg bg-primary-soft p-3 text-sm text-primary"
        >
          {notice}
        </p>
      )}
      <FieldGroup className="gap-5">
        {fields.map(({ name, type, auto }) => (
          <Field key={name} data-invalid={!!errors[name]}>
            <FieldLabel htmlFor={name}>{t(name)}</FieldLabel>
            <Input
              id={name}
              type={type}
              autoComplete={auto}
              aria-invalid={!!errors[name]}
              {...form.register(name)}
            />
            {name === "password" && mode === "register" && !errors.password && (
              <FieldDescription>{t("passwordHint")}</FieldDescription>
            )}
            <FieldError errors={[errors[name]]} />
          </Field>
        ))}
        {mode === "register" && (
          <Field>
            <FieldLabel htmlFor="industry">{t("industry")}</FieldLabel>
            <Controller
              control={form.control}
              name="industry"
              render={({ field }) => (
                <Select value={field.value || undefined} onValueChange={field.onChange}>
                  <SelectTrigger id="industry" className="w-full">
                    <SelectValue placeholder={t("industryPlaceholder")} />
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
      </FieldGroup>
      {formError && (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-lg bg-negative-soft p-3 text-sm text-negative-ink"
        >
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
          {formError}
        </p>
      )}
      <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
        {mode === "login" ? t("submitLogin") : t("submitRegister")}
      </Button>
    </form>
  );
}
