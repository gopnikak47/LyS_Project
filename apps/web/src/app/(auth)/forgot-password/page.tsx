import Link from "next/link";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { ComingSoonState } from "@/components/feedback/states";
import { Button } from "@/components/ui/button";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("auth");
  return { title: t("forgotPassword") };
}

export default async function ForgotPasswordPage() {
  const t = await getTranslations();
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">{t("auth.forgotPassword")}</h1>
      <ComingSoonState
        title={t("states.comingSoonTitle")}
        description={t("states.comingSoonDescription", { stage: 2 })}
        action={
          <Button variant="outline" asChild>
            <Link href="/login">{t("auth.loginTitle")}</Link>
          </Button>
        }
      />
    </div>
  );
}
