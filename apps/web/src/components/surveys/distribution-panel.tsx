"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api/client";
import type { Survey } from "@/lib/api/surveys";
import { Button } from "@/components/ui/button";
export function DistributionPanel({ survey }: { survey: Survey }) {
  const t = useTranslations("engagement");
  const [emails, setEmails] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [embed, setEmbed] = useState("");
  async function send() {
    setError("");
    try {
      const result = await api<{ queued: number }>(`/surveys/${survey.id}/email-invitations`, {
        method: "POST",
        body: { recipients: emails.split(/[\s,;]+/).filter(Boolean) },
      });
      setMessage(t("queued", { count: result.queued }));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function getEmbed() {
    try {
      const result = await api<{ embed: string }>(`/surveys/${survey.id}/share?channel=embed`);
      setEmbed(result.embed);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <section className="space-y-3 rounded-xl border bg-card p-5">
      <h2 className="text-xl font-semibold">{t("distribution")}</h2>
      <label className="block">
        {t("emails")}
        <textarea
          className="block w-full rounded-lg border p-3"
          value={emails}
          onChange={(e) => setEmails(e.target.value)}
        />
      </label>
      <Button
        onClick={() => {
          void send();
        }}
      >
        {t("send")}
      </Button>
      <Button
        variant="outline"
        className="ml-2"
        onClick={() => {
          void getEmbed();
        }}
      >
        {t("embed")}
      </Button>
      <a
        className="ml-3 underline"
        href={`/s/${survey.slug}?channel=kiosk`}
        target="_blank"
        rel="noreferrer"
      >
        {t("kiosk")}
      </a>
      {embed && (
        <textarea
          readOnly
          aria-label={t("embed")}
          className="block w-full rounded-lg border p-3"
          value={embed}
        />
      )}
      <p role="status">{message}</p>
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
