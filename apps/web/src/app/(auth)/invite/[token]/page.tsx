import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { InviteAccept } from "@/components/auth/invite-accept";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("auth");
  return { title: t("inviteTitle"), robots: { index: false } };
}

export default async function InvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return <InviteAccept token={token} />;
}
