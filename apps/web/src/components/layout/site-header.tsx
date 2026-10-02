import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Button } from "@/components/ui/button";
import { Logo } from "./logo";
import { MobileNav } from "./mobile-nav";

export async function SiteHeader() {
  const t = await getTranslations("marketing.nav");
  const links = [
    { href: "/#features", label: t("features") },
    { href: "/pricing", label: t("pricing") },
    { href: "/#steps", label: t("guide") },
    { href: "/#contact", label: t("contact") },
  ];

  return (
    <header className="sticky top-0 z-40 border-b bg-background">
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
        <Logo />
        <nav aria-label={t("label")} className="hidden flex-1 items-center gap-1 md:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              {link.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto hidden items-center gap-2 md:flex">
          <Button variant="ghost" asChild>
            <Link href="/login">{t("login")}</Link>
          </Button>
          <Button asChild>
            <Link href="/register">{t("signupFree")}</Link>
          </Button>
        </div>
        <MobileNav
          className="ml-auto md:hidden"
          links={links}
          actions={[
            { href: "/login", label: t("login"), variant: "outline" },
            { href: "/register", label: t("signupFree"), variant: "default" },
          ]}
        />
      </div>
    </header>
  );
}
