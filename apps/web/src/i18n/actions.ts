"use server";

import { cookies } from "next/headers";
import { LOCALE_COOKIE, isLocale } from "@lys/shared";

/** Đổi ngôn ngữ giao diện: ghi cookie, trang sẽ được render lại bằng router.refresh(). */
export async function setLocale(locale: string): Promise<void> {
  if (!isLocale(locale)) return;
  const store = await cookies();
  store.set(LOCALE_COOKIE, locale, {
    path: "/",
    maxAge: 60 * 60 * 24 * 365,
    sameSite: "lax",
  });
}
