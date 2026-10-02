"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { standardSchemaResolver } from "@hookform/resolvers/standard-schema";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { TopicChip } from "@/components/feedback/topic-chip";
import { api } from "@/lib/api/client";
import type { Topic, TopicTemplate } from "@/lib/api/types";

type TopicValues = { name: string; description: string; keywords: string; color: string };
export type TopicPayload = {
  name: string;
  description: string | null;
  keywords: string[];
  color: string;
};

/** Thêm/sửa chủ đề. Từ khóa nhập dạng chuỗi phân tách bằng dấu phẩy. */
export function TopicDialog({
  topic,
  open,
  onOpenChange,
  onSubmit,
  pending,
}: {
  topic: Topic | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: TopicPayload) => void;
  pending: boolean;
}) {
  const t = useTranslations("topics");
  const tc = useTranslations("common");
  const tv = useTranslations("validation");
  const form = useForm<TopicValues>({
    resolver: standardSchemaResolver(
      z.object({
        name: z
          .string()
          .trim()
          .min(1, tv("required"))
          .max(100, tv("maxLength", { max: 100 })),
        description: z.string().max(500, tv("maxLength", { max: 500 })),
        keywords: z.string().max(5000),
        color: z.string().regex(/^#[0-9a-fA-F]{6}$/),
      }),
    ),
    values: {
      name: topic?.name ?? "",
      description: topic?.description ?? "",
      keywords: topic?.keywords.join(", ") ?? "",
      color: topic?.color ?? "#6366f1",
    },
  });
  const { errors } = form.formState;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{topic ? t("edit") : t("add")}</DialogTitle>
          <DialogDescription className="sr-only">{t("descriptionHint")}</DialogDescription>
        </DialogHeader>
        <form
          id="topic-form"
          noValidate
          onSubmit={form.handleSubmit((v) =>
            onSubmit({
              name: v.name.trim(),
              description: v.description.trim() || null,
              keywords: v.keywords
                .split(",")
                .map((k) => k.trim())
                .filter(Boolean),
              color: v.color,
            }),
          )}
        >
          <FieldGroup className="gap-4">
            <Field data-invalid={!!errors.name}>
              <FieldLabel htmlFor="topic-name">{t("name")}</FieldLabel>
              <Input id="topic-name" {...form.register("name")} />
              <FieldError errors={[errors.name]} />
            </Field>
            <Field data-invalid={!!errors.description}>
              <FieldLabel htmlFor="topic-description">{t("description")}</FieldLabel>
              <Textarea id="topic-description" rows={2} {...form.register("description")} />
              <FieldDescription>{t("descriptionHint")}</FieldDescription>
              <FieldError errors={[errors.description]} />
            </Field>
            <Field>
              <FieldLabel htmlFor="topic-keywords">{t("keywords")}</FieldLabel>
              <Textarea id="topic-keywords" rows={2} {...form.register("keywords")} />
              <FieldDescription>{t("keywordsHint")}</FieldDescription>
            </Field>
            <Field orientation="horizontal">
              <input
                id="topic-color"
                type="color"
                className="h-9 w-12 cursor-pointer rounded-md border"
                {...form.register("color")}
              />
              <FieldLabel htmlFor="topic-color" className="font-normal">
                {t("color")}
              </FieldLabel>
            </Field>
          </FieldGroup>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {tc("cancel")}
          </Button>
          <Button type="submit" form="topic-form" disabled={pending}>
            {pending && <Loader2 className="animate-spin" aria-hidden />}
            {tc("save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function MergeDialog({
  sources,
  candidates,
  open,
  onOpenChange,
  onMerge,
  pending,
}: {
  sources: Topic[];
  candidates: Topic[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onMerge: (targetId: string) => void;
  pending: boolean;
}) {
  const t = useTranslations("topics");
  const tc = useTranslations("common");
  const [target, setTarget] = useState<string>("");
  const options = candidates.filter((c) => !sources.some((s) => s.id === c.id));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("mergeTitle")}</DialogTitle>
          <DialogDescription>{t("mergeDescription")}</DialogDescription>
        </DialogHeader>
        <div className="flex flex-wrap gap-1.5">
          {sources.map((s) => (
            <TopicChip key={s.id} label={s.name} color={s.color} />
          ))}
        </div>
        <Field>
          <FieldLabel htmlFor="merge-target">{t("mergeTarget")}</FieldLabel>
          <Select value={target} onValueChange={setTarget}>
            <SelectTrigger id="merge-target" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {options.map((o) => (
                <SelectItem key={o.id} value={o.id}>
                  {o.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {tc("cancel")}
          </Button>
          <Button disabled={!target || pending} onClick={() => onMerge(target)}>
            {pending && <Loader2 className="animate-spin" aria-hidden />}
            {t("merge")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function TemplateDialog({
  open,
  onOpenChange,
  onApply,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onApply: (code: string, replace: boolean) => Promise<unknown>;
}) {
  const t = useTranslations("topics");
  const tc = useTranslations("common");
  const [code, setCode] = useState("restaurant");
  const [mode, setMode] = useState<"append" | "replace">("append");
  const templates = useQuery({
    queryKey: ["topic-templates"],
    queryFn: () => api<TopicTemplate[]>("/topic-templates"),
    enabled: open,
    staleTime: Infinity,
  });
  const apply = useMutation({ mutationFn: () => onApply(code, mode === "replace") });
  const selected = templates.data?.find((x) => x.code === code);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("templateTitle")}</DialogTitle>
          <DialogDescription className="sr-only">{t("template")}</DialogDescription>
        </DialogHeader>
        {templates.isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <div className="space-y-4">
            <Select value={code} onValueChange={setCode}>
              <SelectTrigger className="w-full" aria-label={t("templateTitle")}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {templates.data?.map((x) => (
                  <SelectItem key={x.code} value={x.code}>
                    {x.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <ul className="space-y-2 rounded-lg border p-3">
              {selected?.topics.map((x) => (
                <li key={x.name} className="text-sm">
                  <TopicChip label={x.name} color={x.color} />
                  <p className="mt-1 text-xs text-muted-foreground">{x.description}</p>
                </li>
              ))}
            </ul>
            <RadioGroup value={mode} onValueChange={(v) => setMode(v as "append" | "replace")}>
              <div className="flex items-center gap-2">
                <RadioGroupItem id="tpl-append" value="append" />
                <Label htmlFor="tpl-append">{t("templateAppend")}</Label>
              </div>
              <div className="flex items-center gap-2">
                <RadioGroupItem id="tpl-replace" value="replace" />
                <Label htmlFor="tpl-replace">{t("templateReplace")}</Label>
              </div>
            </RadioGroup>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {tc("cancel")}
          </Button>
          <Button
            disabled={!selected || apply.isPending}
            onClick={async () => {
              await apply.mutateAsync();
              onOpenChange(false);
            }}
          >
            {apply.isPending && <Loader2 className="animate-spin" aria-hidden />}
            {tc("confirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
