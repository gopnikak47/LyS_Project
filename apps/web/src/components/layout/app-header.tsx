"use client";

import { useTranslations } from "next-intl";
import type { Permission, Session } from "@/lib/api/types";
import { AppNav } from "./app-nav";
import { LocaleSwitcher } from "./locale-switcher";
import { Logo } from "./logo";
import { MobileNav } from "./mobile-nav";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";
import { WorkspaceSwitcher } from "./workspace-switcher";

export function AppHeader({ session }: { session: Session }) {
  const t = useTranslations("app.nav");
  const can = (p: Permission) => session.permissions.includes(p);
  // Menu chỉ hiện mục người dùng có quyền (API vẫn kiểm tra lại quyền ở mọi endpoint).
  const items = [
    can("survey:edit") && { href: "/surveys/new", label: t("createSurvey") },
    { href: "/surveys", label: t("mySurveys") },
    { href: "/topics", label: t("topics") },
    { href: "/responses", label: t("responses") },
    { href: "/reports", label: t("reports") },
    { href: "/tickets", label: t("tickets") },
    { href: "/profile", label: t("profile") },
    can("tenant:manage") && { href: "/billing", label: t("billing") },
    can("member:manage") && { href: "/admin", label: t("admin") },
  ].filter((item): item is { href: string; label: string } => !!item);

  return (
    <header className="sticky top-0 z-40 border-b bg-card">
      <div className="mx-auto flex h-16 max-w-[90rem] items-center gap-3 px-4 sm:px-6 lg:px-8">
        <MobileNav className="-ml-2 lg:hidden" links={items} />
        <Logo
          href="/surveys"
          className="mr-2 [&>span:last-child]:hidden sm:[&>span:last-child]:inline"
        />
        <div className="hidden md:block">
          <WorkspaceSwitcher />
        </div>
        <div className="mx-2 hidden h-6 w-px bg-border lg:block" aria-hidden />
        <AppNav items={items} label={t("label")} />
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <LocaleSwitcher className="hidden 2xl:inline-flex" />
          <ThemeToggle />
          <UserMenu session={session} />
        </div>
      </div>
      <div className="border-t px-4 py-2 md:hidden">
        <WorkspaceSwitcher />
      </div>
    </header>
  );
}
