"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Check, ChevronsUpDown, Plus, Tags } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { setSelectedWorkspace, useCan, useCurrentWorkspace } from "@/lib/api/hooks";

export function WorkspaceSwitcher() {
  const t = useTranslations("app.workspace");
  const canManage = useCan("workspace:manage");
  const { workspace, workspaces, isLoading } = useCurrentWorkspace();

  if (isLoading) return <Skeleton className="h-9 w-44" />;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="h-9 max-w-[14rem] justify-between gap-2 px-2.5"
          aria-label={t("switch")}
        >
          <span
            aria-hidden
            className="size-2.5 shrink-0 rounded-full"
            style={{ backgroundColor: workspace?.color ?? "var(--muted-foreground)" }}
          />
          <span className="truncate text-sm">{workspace?.name ?? t("empty")}</span>
          <ChevronsUpDown className="size-3.5 opacity-60" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel>{t("label")}</DropdownMenuLabel>
        {workspaces.map((ws) => (
          <DropdownMenuItem key={ws.id} onSelect={() => setSelectedWorkspace(ws.id)}>
            <span
              aria-hidden
              className="size-2.5 rounded-full"
              style={{ backgroundColor: ws.color }}
            />
            <span className="flex-1 truncate">{ws.name}</span>
            {ws.id === workspace?.id && <Check aria-hidden />}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href="/topics">
            <Tags aria-hidden />
            {t("topics")}
          </Link>
        </DropdownMenuItem>
        {canManage && (
          <>
            <DropdownMenuItem asChild>
              <Link href="/admin?tab=workspaces">
                <Plus aria-hidden />
                {t("create")}
              </Link>
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
