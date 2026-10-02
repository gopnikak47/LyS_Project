"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Skeleton } from "@/components/ui/skeleton";
import { isUnauthorized, useSession } from "@/lib/api/hooks";
import { AppHeader } from "./app-header";

/** Khung khu quản trị: chỉ hiển thị nội dung khi phiên hợp lệ; hết phiên → về trang đăng nhập. */
export function AppShell({ children }: { children: React.ReactNode }) {
  const t = useTranslations("app");
  const router = useRouter();
  const pathname = usePathname();
  const session = useSession();

  useEffect(() => {
    if (isUnauthorized(session.error)) {
      router.replace(`/login?expired=1&next=${encodeURIComponent(pathname)}`);
    }
  }, [session.error, router, pathname]);

  if (!session.data) {
    return (
      <div className="flex min-h-dvh flex-col" aria-busy="true">
        <div className="h-16 border-b bg-card" />
        <div className="mx-auto w-full max-w-[90rem] space-y-4 px-4 py-8 sm:px-6 lg:px-8">
          <span className="sr-only" role="status">
            {t("loadingSession")}
          </span>
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96 max-w-full" />
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-40 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <AppHeader session={session.data} />
      <main
        id="main"
        className="mx-auto w-full max-w-[90rem] flex-1 px-4 py-6 sm:px-6 sm:py-8 lg:px-8"
      >
        {children}
      </main>
    </div>
  );
}
