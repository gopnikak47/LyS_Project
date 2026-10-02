"use client";

import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useTranslations } from "next-intl";
import { CircleCheck } from "lucide-react";
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
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

/** Mẫu biểu mẫu chuẩn: react-hook-form + zod, thông báo lỗi tiếng Việt từ i18n. */
export function SurveyFormDemo() {
  const t = useTranslations("uiKit");
  const tv = useTranslations("validation");
  const [saved, setSaved] = useState(false);

  const schema = z.object({
    name: z
      .string()
      .trim()
      .min(3, tv("minLength", { min: 3 }))
      .max(120, tv("maxLength", { max: 120 })),
    description: z.string().max(300, tv("maxLength", { max: 300 })),
    industry: z.enum(INDUSTRIES, tv("select")),
    anonymous: z.boolean(),
  });
  type Values = z.input<typeof schema>;

  const form = useForm<Values>({
    resolver: standardSchemaResolver(schema),
    defaultValues: { name: "", description: "", anonymous: true },
  });
  const { errors } = form.formState;

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit(() => setSaved(true))}
      onChange={() => setSaved(false)}
      className="space-y-6"
    >
      <FieldGroup className="gap-5">
        <Field data-invalid={!!errors.name}>
          <FieldLabel htmlFor="survey-name">{t("formDemo.name")}</FieldLabel>
          <Input
            id="survey-name"
            placeholder={t("formDemo.namePlaceholder")}
            aria-invalid={!!errors.name}
            {...form.register("name")}
          />
          <FieldError errors={[errors.name]} />
        </Field>

        <Field data-invalid={!!errors.description}>
          <FieldLabel htmlFor="survey-description">{t("formDemo.description")}</FieldLabel>
          <Textarea
            id="survey-description"
            rows={3}
            aria-invalid={!!errors.description}
            {...form.register("description")}
          />
          <FieldDescription>{t("formDemo.descriptionHint")}</FieldDescription>
          <FieldError errors={[errors.description]} />
        </Field>

        <Field data-invalid={!!errors.industry}>
          <FieldLabel htmlFor="survey-industry">{t("formDemo.industry")}</FieldLabel>
          <Controller
            control={form.control}
            name="industry"
            render={({ field }) => (
              <Select value={field.value ?? ""} onValueChange={field.onChange}>
                <SelectTrigger
                  id="survey-industry"
                  className="w-full"
                  aria-invalid={!!errors.industry}
                >
                  <SelectValue placeholder={t("formDemo.industryPlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  {INDUSTRIES.map((industry) => (
                    <SelectItem key={industry} value={industry}>
                      {t(`industries.${industry}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          />
          <FieldError errors={[errors.industry]} />
        </Field>

        <Field orientation="horizontal">
          <Controller
            control={form.control}
            name="anonymous"
            render={({ field }) => (
              <Switch
                id="survey-anonymous"
                checked={field.value}
                onCheckedChange={field.onChange}
              />
            )}
          />
          <FieldLabel htmlFor="survey-anonymous" className="font-normal">
            {t("formDemo.anonymous")}
          </FieldLabel>
        </Field>
      </FieldGroup>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit">{t("formDemo.submit")}</Button>
        {saved && (
          <p role="status" className="flex items-center gap-1.5 text-sm text-positive-ink">
            <CircleCheck className="size-4" aria-hidden />
            {t("formDemo.submitted")}
          </p>
        )}
      </div>
    </form>
  );
}
