"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Check, ChevronsUpDown, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Dữ liệu minh họa — danh sách workspace thật lấy từ API ở Giai đoạn 2.
const DEMO_WORKSPACES = [
  { id: "w1", name: "Nhà hàng Quận 1", color: "bg-amber-500" },
  { id: "w2", name: "Ứng dụng đặt bàn", color: "bg-sky-500" },
];

export function WorkspaceSwitcher() {
  const t = useTranslations("app.workspace");
  const [current, setCurrent] = useState(DEMO_WORKSPACES[0]!);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="h-9 max-w-[14rem] justify-between gap-2 px-2.5"
          aria-label={t("switch")}
        >
          <span aria-hidden className={`size-2.5 shrink-0 rounded-full ${current.color}`} />
          <span className="truncate text-sm">{current.name}</span>
          <ChevronsUpDown className="size-3.5 opacity-60" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuLabel>{t("label")}</DropdownMenuLabel>
        {DEMO_WORKSPACES.map((ws) => (
          <DropdownMenuItem key={ws.id} onSelect={() => setCurrent(ws)}>
            <span aria-hidden className={`size-2.5 rounded-full ${ws.color}`} />
            <span className="flex-1 truncate">{ws.name}</span>
            {ws.id === current.id && <Check aria-hidden />}
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled>
          <Plus aria-hidden />
          {t("create")}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
