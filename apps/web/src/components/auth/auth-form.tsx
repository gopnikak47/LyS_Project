"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useTranslations } from "next-intl";
import { Info } from "lucide-react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

type Mode = "login" | "register";

/**
 * Biểu mẫu đăng nhập/đăng ký — Giai đoạn 0 chỉ có giao diện + validate phía client.
 * Gọi API thật ở Giai đoạn 2 (FR-01).
 */
export function AuthForm({ mode }: { mode: Mode }) {
  const t = useTranslations("auth");
  const tv = useTranslations("validation");
  const [notice, setNotice] = useState(false);

  const base = {
    email: z.email(tv("email")),
    password: z.string().min(8, tv("minLength", { min: 8 })),
  };
  const schema =
    mode === "register"
      ? z.object({
          ...base,
          companyName: z
            .string()
            .trim()
            .min(2, tv("minLength", { min: 2 })),
          fullName: z
            .string()
            .trim()
            .min(2, tv("minLength", { min: 2 })),
        })
      : z.object(base);

  type Values = { email: string; password: string; companyName?: string; fullName?: string };

  const form = useForm<Values>({
    resolver: standardSchemaResolver(schema),
    defaultValues: { email: "", password: "", companyName: "", fullName: "" },
  });
  const { errors } = form.formState;

  const fields: { name: keyof Values; type: string; autoComplete: string }[] = [
    ...(mode === "register"
      ? [
          { name: "companyName" as const, type: "text", autoComplete: "organization" },
          { name: "fullName" as const, type: "text", autoComplete: "name" },
        ]
      : []),
    { name: "email", type: "email", autoComplete: "email" },
    {
      name: "password",
      type: "password",
      autoComplete: mode === "login" ? "current-password" : "new-password",
    },
  ];

  return (
    <form noValidate onSubmit={form.handleSubmit(() => setNotice(true))} className="space-y-6">
      <FieldGroup className="gap-5">
        {fields.map(({ name, type, autoComplete }) => (
          <Field key={name} data-invalid={!!errors[name]}>
            <FieldLabel htmlFor={name}>{t(name)}</FieldLabel>
            <Input
              id={name}
              type={type}
              autoComplete={autoComplete}
              aria-invalid={!!errors[name]}
              {...form.register(name)}
            />
            <FieldError errors={[errors[name]]} />
          </Field>
        ))}
      </FieldGroup>
      {notice && (
        <p
          role="status"
          className="flex items-start gap-2 rounded-lg bg-primary-soft p-3 text-sm text-primary"
        >
          <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
          {t("notReady")}
        </p>
      )}
      <Button type="submit" size="lg" className="w-full">
        {mode === "login" ? t("submitLogin") : t("submitRegister")}
      </Button>
    </form>
  );
}
