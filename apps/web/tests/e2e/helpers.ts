import { expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

export const PASSWORD = "MatKhau@2026";

export function uniqueEmail(prefix = "e2e"): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}@vidu.vn`;
}

/** Đăng ký nhanh qua API (dùng chung cookie với trình duyệt của test). */
export async function registerViaApi(
  page: Page,
  {
    company = "Công ty E2E",
    industry = "restaurant",
  }: { company?: string; industry?: string } = {},
) {
  const email = uniqueEmail();
  const res = await page.request.post("/api/v1/auth/register", {
    data: {
      company_name: company,
      full_name: "Người Kiểm Thử",
      email,
      password: PASSWORD,
      industry,
    },
  });
  expect(res.status(), await res.text()).toBe(201);
  return { email, session: await res.json() };
}

/** Không được có thanh cuộn ngang ở bất kỳ kích thước màn hình nào. */
export async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
}

/** Không có lỗi a11y mức nghiêm trọng (mục tiêu Lighthouse Accessibility ≥ 90). */
export async function expectNoSeriousA11yViolations(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(
    serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`),
  ).toEqual([]);
}
