import { Suspense } from "react";
import Link from "next/link";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { AuthForm } from "@/components/auth/auth-form";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { APP_NAME } from "@/lib/config";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("auth");
  return { title: t("loginTitle") };
}

export default async function LoginPage() {
  const t = await getTranslations("auth");
  return (
    <Card className="p-2 sm:p-4">
      <CardHeader>
        <CardTitle className="text-2xl">
          <h1>{t("loginTitle")}</h1>
        </CardTitle>
        <CardDescription>{t("loginSubtitle", { appName: APP_NAME })}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <Suspense>
          <AuthForm mode="login" />
        </Suspense>
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <Link href="/forgot-password" className="text-primary hover:underline">
            {t("forgotPassword")}
          </Link>
          <span className="text-muted-foreground">
            {t("noAccount")}{" "}
            <Link href="/register" className="font-medium text-primary hover:underline">
              {t("registerTitle")}
            </Link>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
