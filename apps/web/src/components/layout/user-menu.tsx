"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Building2, Check, LogOut, Palette, UserRound } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLogout, useSwitchTenant } from "@/lib/api/hooks";
import type { Session } from "@/lib/api/types";

export function initials(name: string): string {
  const words = name.trim().split(/\s+/);
  const picked = words.length > 1 ? [words.at(-2), words.at(-1)] : [words[0]];
  return picked
    .map((w) => w?.[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2);
}

export function UserMenu({ session }: { session: Session }) {
  const t = useTranslations("app");
  const tr = useTranslations("roles");
  const logout = useLogout();
  const switchTenant = useSwitchTenant();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="rounded-full" aria-label={t("user.menu")}>
          <Avatar className="size-9">
            <AvatarFallback className="bg-primary-soft text-sm font-semibold text-primary">
              {initials(session.user.full_name)}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="font-normal">
          <p className="font-medium">{session.user.full_name}</p>
          <p className="truncate text-xs text-muted-foreground">{session.user.email}</p>
          <p className="mt-1 truncate text-xs text-muted-foreground">
            {session.tenant.name} · {tr(session.role)}
          </p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/profile">
            <UserRound aria-hidden />
            {t("user.profile")}
          </Link>
        </DropdownMenuItem>
        {session.memberships.length > 1 && (
          <DropdownMenuSub>
            <DropdownMenuSubTrigger>
              <Building2 aria-hidden />
              {t("user.switchTenant")}
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent className="w-60">
              {session.memberships.map((m) => (
                <DropdownMenuItem
                  key={m.tenant_id}
                  disabled={switchTenant.isPending}
                  onSelect={() =>
                    m.tenant_id !== session.tenant.id && switchTenant.mutate(m.tenant_id)
                  }
                >
                  <span className="flex-1 truncate">{m.tenant_name}</span>
                  {m.tenant_id === session.tenant.id && <Check aria-hidden />}
                </DropdownMenuItem>
              ))}
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        )}
        <DropdownMenuItem asChild>
          <Link href="/ui-kit">
            <Palette aria-hidden />
            {t("nav.uiKit")}
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => logout.mutate()} disabled={logout.isPending}>
          <LogOut aria-hidden />
          {t("user.logout")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
