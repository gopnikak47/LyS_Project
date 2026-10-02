"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export type AppNavItem = { href: string; label: string };

/** Thanh điều hướng chính khu quản trị, đánh dấu mục đang mở (aria-current). */
export function AppNav({ items, label }: { items: AppNavItem[]; label: string }) {
  const pathname = usePathname();
  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);
  // Mục có đường dẫn dài nhất khớp được coi là đang mở (ví dụ /surveys/new thắng /surveys).
  const active = items
    .filter((item) => isActive(item.href))
    .sort((a, b) => b.href.length - a.href.length)[0]?.href;

  return (
    <nav aria-label={label} className="hidden items-center gap-1 lg:flex">
      {items.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          aria-current={item.href === active ? "page" : undefined}
          className={cn(
            "rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground",
            "aria-[current=page]:bg-primary-soft aria-[current=page]:text-primary",
          )}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
