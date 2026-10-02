import { render, type RenderOptions } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import vi from "@lys/shared/i18n/vi.json";

/** Render component trong ngữ cảnh i18n tiếng Việt (ngôn ngữ mặc định). */
export function renderWithIntl(ui: React.ReactElement, options?: RenderOptions) {
  return render(
    <NextIntlClientProvider locale="vi" messages={vi} timeZone="Asia/Ho_Chi_Minh">
      {ui}
    </NextIntlClientProvider>,
    options,
  );
}
