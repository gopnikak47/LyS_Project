import { Suspense } from "react";
import Link from "next/link";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AuthForm } from "@/components/auth/auth-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("auth");
  return { title: t("registerTitle") };
}

export default async function RegisterPage() {
  const t = await getTranslations("auth");
  return (
    <Card className="p-2 sm:p-4">
      <CardHeader>
        <CardTitle className="text-2xl">
          <h1>{t("registerTitle")}</h1>
        </CardTitle>
        <CardDescription>{t("registerSubtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <Suspense>
          <AuthForm mode="register" />
        </Suspense>
        <p className="text-center text-sm text-muted-foreground">
          {t("hasAccount")}{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            {t("loginTitle")}
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
