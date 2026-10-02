import { getTranslations } from "next-intl/server";
import { AppNav } from "./app-nav";
import { LocaleSwitcher } from "./locale-switcher";
import { Logo } from "./logo";
import { MobileNav } from "./mobile-nav";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";
import { WorkspaceSwitcher } from "./workspace-switcher";

export async function AppHeader() {
  const t = await getTranslations("app.nav");
  const items = [
    { href: "/surveys/new", label: t("createSurvey") },
    { href: "/surveys", label: t("mySurveys") },
    { href: "/profile", label: t("profile") },
    { href: "/billing", label: t("billing") },
    { href: "/admin", label: t("admin") },
  ];

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
          <LocaleSwitcher className="hidden xl:inline-flex" />
          <ThemeToggle />
          <UserMenu />
        </div>
      </div>
      <div className="border-t px-4 py-2 md:hidden">
        <WorkspaceSwitcher />
      </div>
    </header>
  );
}
