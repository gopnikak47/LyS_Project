import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/** Không được có thanh cuộn ngang ở bất kỳ kích thước màn hình nào. */
async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(0);
}

/** Không có lỗi a11y mức nghiêm trọng (mục tiêu Lighthouse Accessibility ≥ 90). */
async function expectNoSeriousA11yViolations(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(
    serious.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`),
  ).toEqual([]);
}

test("landing page: hero, tính năng, FAQ", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Lắng nghe khách hàng");
  await expect(page.getByRole("link", { name: "Tạo khảo sát miễn phí ngay" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Tạo khảo sát trong 3 bước" })).toBeVisible();

  await page.getByRole("tab", { name: "Phân tích NLP" }).click();
  await expect(page.getByRole("tabpanel")).toContainText("teencode");

  await page.getByRole("button", { name: /cần đăng nhập/ }).click();
  await expect(page.getByText("Khách chỉ cần mở link")).toBeVisible();

  await expectNoHorizontalScroll(page);
  await expectNoSeriousA11yViolations(page);
});

test("khu quản trị: khảo sát của tôi", async ({ page, isMobile }) => {
  await page.goto("/surveys");
  await expect(page.getByRole("heading", { level: 1, name: "Khảo sát của tôi" })).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Khảo sát hài lòng – Chi nhánh Quận 1" }),
  ).toBeVisible();

  if (isMobile) {
    await page.getByRole("button", { name: "Mở menu" }).click();
    await expect(
      page.getByRole("dialog").getByRole("link", { name: "Gói & Thanh toán" }),
    ).toBeVisible();
    await page.keyboard.press("Escape");
  }

  await expectNoHorizontalScroll(page);
  await expectNoSeriousA11yViolations(page);
});

test("thư viện giao diện: biểu mẫu validate tiếng Việt", async ({ page }) => {
  await page.goto("/ui-kit");
  await expect(page.getByRole("heading", { name: "Bảng phản hồi" })).toBeVisible();
  // Phản hồi khẩn cấp được ghim ở dòng đầu.
  await expect(page.locator("tbody tr").first()).toHaveAttribute("data-urgent", "true");

  await page.getByRole("button", { name: "Lưu thử" }).click();
  await expect(page.getByText("Cần tối thiểu 3 ký tự.")).toBeVisible();
  await expect(page.getByText("Vui lòng chọn một mục.")).toBeVisible();

  await expectNoSeriousA11yViolations(page);
});

test("đổi ngôn ngữ sang tiếng Anh và quay lại", async ({ page }) => {
  await page.goto("/");
  const footer = page.getByRole("contentinfo");
  await footer.getByRole("combobox").selectOption("en");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Listen to customers");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");

  await footer.getByRole("combobox").selectOption("vi");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Lắng nghe khách hàng");
});

test("trang 404 thân thiện", async ({ page }) => {
  const res = await page.goto("/khong-ton-tai/abc");
  expect(res?.status()).toBe(404);
  await expect(page.getByText("Không tìm thấy trang")).toBeVisible();
});
