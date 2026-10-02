import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, expectNoSeriousA11yViolations, registerViaApi } from "./helpers";

test("chủ đề: bộ mẫu ngành, thêm, gộp, áp mẫu khác", async ({ page }) => {
  await registerViaApi(page, { industry: "restaurant" });
  await page.goto("/topics");
  await expect(page.getByRole("heading", { level: 1, name: "Chủ đề phân tích" })).toBeVisible();
  for (const name of ["Món ăn", "Phục vụ", "Giá cả", "Không gian", "Vệ sinh"]) {
    await expect(page.getByRole("heading", { level: 3, name })).toBeVisible();
  }

  await page.getByRole("button", { name: "Thêm chủ đề" }).click();
  await page.getByRole("dialog").getByLabel("Tên chủ đề").fill("Giao hàng");
  await page.getByRole("dialog").getByLabel("Từ khóa gợi ý").fill("ship, giao trễ, đóng gói");
  await page.getByRole("button", { name: "Lưu" }).click();
  await expect(page.getByRole("heading", { level: 3, name: "Giao hàng" })).toBeVisible();
  await expect(page.getByText("giao trễ")).toBeVisible();

  await page.getByRole("checkbox", { name: "Chọn “Giao hàng”" }).check();
  await page.getByRole("button", { name: /Gộp 1 chủ đề/ }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("combobox", { name: "Gộp vào" }).click();
  await page.getByRole("option", { name: "Phục vụ" }).click();
  await dialog.getByRole("button", { name: "Gộp" }).click();
  await expect(page.getByRole("heading", { level: 3, name: "Giao hàng" })).toHaveCount(0);

  await expectNoHorizontalScroll(page);
  await expectNoSeriousA11yViolations(page);

  await page.getByRole("button", { name: "Dùng bộ mẫu theo ngành" }).click();
  await page.getByRole("dialog").getByRole("combobox").click();
  await page.getByRole("option", { name: "Khách sạn" }).click();
  await page.getByLabel("Thay thế toàn bộ").check();
  await page.getByRole("dialog").getByRole("button", { name: "Xác nhận" }).click();
  await expect(page.getByRole("heading", { level: 3, name: "Phòng ở" })).toBeVisible();
  await expect(page.getByRole("heading", { level: 3, name: "Món ăn" })).toHaveCount(0);
});
