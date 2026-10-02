"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { LogOut, Palette, UserRound } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Người dùng minh họa — thay bằng phiên đăng nhập thật ở Giai đoạn 2.
const DEMO_USER = { name: "Nguyễn Minh An", email: "an.nguyen@example.com", initials: "MA" };

export function UserMenu() {
  const t = useTranslations("app");

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="rounded-full" aria-label={t("user.menu")}>
          <Avatar className="size-9">
            <AvatarFallback className="bg-primary-soft text-sm font-semibold text-primary">
              {DEMO_USER.initials}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-60">
        <DropdownMenuLabel className="font-normal">
          <p className="font-medium">{DEMO_USER.name}</p>
          <p className="truncate text-xs text-muted-foreground">{DEMO_USER.email}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/profile">
            <UserRound aria-hidden />
            {t("user.profile")}
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link href="/ui-kit">
            <Palette aria-hidden />
            {t("nav.uiKit")}
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled>
          <LogOut aria-hidden />
          {t("user.logout")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
