import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, expectNoSeriousA11yViolations, registerViaApi } from "./helpers";

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

test("khu quản trị yêu cầu đăng nhập", async ({ page }) => {
  await page.goto("/surveys");
  await expect(page).toHaveURL(/\/login\?next=%2Fsurveys/);
});

test("khu quản trị: khảo sát của tôi", async ({ page, isMobile }) => {
  await registerViaApi(page);
  await page.goto("/surveys");
  await expect(page.getByRole("heading", { level: 1, name: "Khảo sát của tôi" })).toBeVisible();

  if (isMobile) {
    await page.getByRole("button", { name: "Mở menu" }).click();
    await expect(page.getByRole("dialog").getByRole("link", { name: "Quản lý" })).toBeVisible();
    await page.keyboard.press("Escape");
  }

  await expectNoHorizontalScroll(page);
  await expectNoSeriousA11yViolations(page);
});

test("thư viện giao diện: biểu mẫu validate tiếng Việt", async ({ page }) => {
  await registerViaApi(page);
  await page.goto("/ui-kit");
  await expect(page.getByRole("heading", { name: "Bảng phản hồi" })).toBeVisible();
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
