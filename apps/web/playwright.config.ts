import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.WEB_PORT ?? 3000);
const baseURL = process.env.E2E_BASE_URL ?? `http://localhost:${PORT}`;
// Cho phép dùng Chromium có sẵn trên máy (ví dụ môi trường không tải được trình duyệt).
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined;
const chromium = { ...devices["Desktop Chrome"], launchOptions: { executablePath } };

// Ba kích thước bắt buộc theo Definition of Done: 375 / 768 / 1280.
const viewports = [
  { name: "mobile-375", viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true },
  { name: "tablet-768", viewport: { width: 768, height: 1024 }, isMobile: false, hasTouch: true },
  {
    name: "desktop-1280",
    viewport: { width: 1280, height: 800 },
    isMobile: false,
    hasTouch: false,
  },
];

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: { baseURL, trace: "retain-on-failure", locale: "vi-VN", timezoneId: "Asia/Ho_Chi_Minh" },
  projects: [
    ...viewports.map(({ name, ...device }) => ({
      name,
      testIgnore: /screenshots\.spec\.ts/,
      use: { ...chromium, ...device },
    })),
    {
      name: "screenshots",
      testMatch: /screenshots\.spec\.ts/,
      use: { ...chromium },
    },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: process.env.CI ? `pnpm start --port ${PORT}` : `pnpm dev --port ${PORT}`,
        url: `${baseURL}/healthz`,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
