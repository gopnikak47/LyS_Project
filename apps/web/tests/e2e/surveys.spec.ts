import { expect, test } from "@playwright/test";
import { registerViaApi, expectNoHorizontalScroll } from "./helpers";

test("published survey accepts feedback and shows it to its owner", async ({ page, browser }) => {
  const { session } = await registerViaApi(page);
  const headers = { "X-CSRF-Token": session.csrf_token };
  const workspaces = await (await page.request.get("/api/v1/workspaces")).json();
  const created = await page.request.post("/api/v1/surveys", {
    headers,
    data: {
      workspace_id: workspaces[0].id,
      title: "Khảo sát E2E",
      questions: [
        { code: "rating", type: "rating", title: { vi: "Chấm điểm" }, required: true },
        { code: "comment", type: "text", title: { vi: "Góp ý" }, required: true },
      ],
    },
  });
  expect(created.status(), await created.text()).toBe(201);
  const survey = await created.json();
  const published = await page.request.post(`/api/v1/surveys/${survey.id}/publish`, { headers });
  expect(published.status(), await published.text()).toBe(200);
  const guestContext = await browser.newContext({
    baseURL: test.info().project.use.baseURL,
    viewport: page.viewportSize() || undefined,
  });
  const guest = await guestContext.newPage();
  await guest.goto(`/s/${survey.slug}`);
  await guest.getByRole("radio").first().check();
  await guest.getByRole("textbox", { name: "Góp ý" }).fill("Nhận xét E2E về phục vụ");
  await expectNoHorizontalScroll(guest);
  // The server requires at least two seconds per attempt to reject instant bot submissions.
  await expect
    .poll(async () =>
      guest.evaluate(() => {
        const stored = Object.keys(sessionStorage).find((key) => key.endsWith(":attempt"));
        return stored
          ? Date.now() / 1000 - JSON.parse(sessionStorage.getItem(stored)!).started_at
          : 0;
      }),
    )
    .toBeGreaterThan(2);
  const submit = guest.getByRole("button", { name: "Gửi phản hồi", exact: true });
  await submit.click();
  await expect(guest.getByRole("heading", { name: "Cảm ơn bạn!", exact: true })).toBeVisible();
  await page.goto("/responses");
  await expect(page.getByText("Nhận xét E2E về phục vụ", { exact: true })).toBeVisible();
  await guestContext.close();
});
