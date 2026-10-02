import type { Locale } from "@lys/shared";
import type messages from "@lys/shared/i18n/vi.json";

// Kiểu an toàn cho khóa dịch: dùng sai khóa sẽ báo lỗi khi type-check.
declare module "next-intl" {
  interface AppConfig {
    Locale: Locale;
    Messages: typeof messages;
  }
}
