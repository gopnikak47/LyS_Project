import { test } from "@playwright/test";

/**
 * Chụp ảnh màn hình các trang mẫu ở 3 kích thước, lưu vào docs/screenshots/.
 * Chạy: `pnpm --filter @lys/web screenshots`
 */
const PAGES = [
  { path: "/", name: "landing" },
  { path: "/surveys", name: "surveys" },
  { path: "/ui-kit", name: "ui-kit" },
  { path: "/login", name: "login" },
];
const SIZES = [
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1280, height: 800 },
];
const OUT_DIR = new URL("../../../../docs/screenshots/", import.meta.url).pathname;

for (const { path, name } of PAGES) {
  for (const size of SIZES) {
    test(`${name} @ ${size.width}px`, async ({ page }) => {
      await page.setViewportSize(size);
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: `${OUT_DIR}${name}-${size.width}.png`, fullPage: true });
    });
  }
}
