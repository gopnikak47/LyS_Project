import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { APP_NAME } from "@/lib/config";
import { LocaleSwitcher } from "./locale-switcher";
import { Logo } from "./logo";

export async function SiteFooter() {
  const t = await getTranslations("marketing");
  const columns = [
    {
      title: t("footer.product"),
      links: [
        { href: "/#features", label: t("nav.features") },
        { href: "/pricing", label: t("nav.pricing") },
        { href: "/templates", label: t("footer.templates") },
      ],
    },
    {
      title: t("footer.resources"),
      links: [
        { href: "/#steps", label: t("nav.guide") },
        { href: "/docs", label: t("footer.docs") },
        { href: "/#faq", label: t("faq.title") },
      ],
    },
    {
      title: t("footer.company"),
      links: [
        { href: "/about", label: t("footer.about") },
        { href: "/privacy", label: t("footer.privacy") },
        { href: "/terms", label: t("footer.terms") },
      ],
    },
  ];

  return (
    <footer id="contact" className="border-t bg-card">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 sm:px-6 md:grid-cols-[1.5fr_repeat(3,1fr)] lg:px-8">
        <div className="space-y-4">
          <Logo />
          <p className="max-w-xs text-sm text-muted-foreground">{t("footer.tagline")}</p>
          <LocaleSwitcher />
        </div>
        {columns.map((column) => (
          <div key={column.title}>
            <h2 className="text-sm font-semibold">{column.title}</h2>
            <ul className="mt-3 space-y-2">
              {column.links.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t">
        <p className="mx-auto max-w-7xl px-4 py-5 text-xs text-muted-foreground sm:px-6 lg:px-8">
          {t("footer.rights", { year: new Date().getFullYear(), appName: APP_NAME })}
        </p>
      </div>
    </footer>
  );
}
