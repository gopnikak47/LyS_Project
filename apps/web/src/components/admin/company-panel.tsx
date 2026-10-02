"use client";

import { useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api/client";
import { queryKeys, useSession } from "@/lib/api/hooks";
import type { TenantOut } from "@/lib/api/types";

export function CompanyPanel() {
  const t = useTranslations("admin.company");
  const tc = useTranslations("common");
  const { data: session } = useSession();
  const client = useQueryClient();
  const form = useForm<{ name: string }>({ values: { name: session?.tenant.name ?? "" } });
  const save = useMutation({
    mutationFn: (name: string) =>
      api<TenantOut>("/tenants/me", { method: "PATCH", body: { name } }),
    onSuccess: () => {
      toast.success(tc("saved"));
      client.invalidateQueries({ queryKey: queryKeys.session });
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.message : tc("errorGeneric")),
  });

  return (
    <Card className="max-w-xl">
      <CardContent>
        <form className="space-y-5" onSubmit={form.handleSubmit(({ name }) => save.mutate(name))}>
          <FieldGroup className="gap-4">
            <Field>
              <FieldLabel htmlFor="tenant-name">{t("name")}</FieldLabel>
              <Input
                id="tenant-name"
                {...form.register("name", { required: true, minLength: 2 })}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="tenant-slug">{t("slug")}</FieldLabel>
              <Input id="tenant-slug" value={session?.tenant.slug ?? ""} readOnly disabled />
            </Field>
            <Field>
              <FieldLabel htmlFor="tenant-plan">{t("plan")}</FieldLabel>
              <Input
                id="tenant-plan"
                value={session?.tenant.plan_code.toUpperCase() ?? ""}
                readOnly
                disabled
              />
            </Field>
          </FieldGroup>
          <Button type="submit" disabled={save.isPending}>
            {save.isPending && <Loader2 className="animate-spin" aria-hidden />}
            {tc("save")}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
