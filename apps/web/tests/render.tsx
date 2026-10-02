import { render, type RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NextIntlClientProvider } from "next-intl";
import vi from "@lys/shared/i18n/vi.json";

/** Render component trong ngữ cảnh i18n tiếng Việt + TanStack Query (không retry). */
export function renderWithIntl(ui: React.ReactElement, options?: RenderOptions) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <NextIntlClientProvider locale="vi" messages={vi} timeZone="Asia/Ho_Chi_Minh">
        {ui}
      </NextIntlClientProvider>
    </QueryClientProvider>,
    options,
  );
}
