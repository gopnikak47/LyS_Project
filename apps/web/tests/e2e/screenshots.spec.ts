import { test } from "@playwright/test";
import { registerViaApi } from "./helpers";

/**
 * Chụp ảnh màn hình các trang mẫu ở 3 kích thước, lưu vào docs/screenshots/.
 * Chạy: `pnpm --filter @lys/web screenshots`
 */
const PAGES = [
  { path: "/", name: "landing", auth: false },
  { path: "/login", name: "login", auth: false },
  { path: "/surveys", name: "surveys", auth: true },
  { path: "/ui-kit", name: "ui-kit", auth: true },
  { path: "/admin?tab=invitations", name: "admin", auth: true },
];
const SIZES = [
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1280, height: 800 },
];
const OUT_DIR = new URL("../../../../docs/screenshots/", import.meta.url).pathname;

for (const { path, name, auth } of PAGES) {
  for (const size of SIZES) {
    test(`${name} @ ${size.width}px`, async ({ page }) => {
      await page.setViewportSize(size);
      if (auth) await registerViaApi(page, { company: "Chuỗi nhà hàng Phố Xưa" });
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await page.evaluate(() => document.fonts.ready);
      await page.screenshot({ path: `${OUT_DIR}${name}-${size.width}.png`, fullPage: true });
    });
  }
}
