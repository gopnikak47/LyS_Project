import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";
import { DEFAULT_LOCALE, LOCALE_COOKIE, isLocale, type Locale } from "@lys/shared";
import type viMessages from "@lys/shared/i18n/vi.json";

type Messages = typeof viMessages;

/*
 * i18n không dùng tiền tố URL (/vi, /en): link khảo sát công khai `/s/{slug}` luôn ổn định.
 * Ngôn ngữ giao diện lấy từ cookie NEXT_LOCALE, mặc định tiếng Việt.
 */
const loaders: Record<Locale, () => Promise<{ default: Messages }>> = {
  vi: () => import("@lys/shared/i18n/vi.json"),
  en: () => import("@lys/shared/i18n/en.json"),
};

export default getRequestConfig(async () => {
  const store = await cookies();
  const fromCookie = store.get(LOCALE_COOKIE)?.value;
  const locale: Locale = isLocale(fromCookie) ? fromCookie : DEFAULT_LOCALE;

  return {
    locale,
    messages: (await loaders[locale]()).default,
    timeZone: "Asia/Ho_Chi_Minh",
  };
});
