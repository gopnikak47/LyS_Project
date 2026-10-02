import { expect, test } from "@playwright/test";
import {
  PASSWORD,
  expectNoHorizontalScroll,
  expectNoSeriousA11yViolations,
  registerViaApi,
  uniqueEmail,
} from "./helpers";

test("đăng ký doanh nghiệp qua giao diện → vào khu quản trị", async ({ page }) => {
  const email = uniqueEmail("dk");
  await page.goto("/register");
  await page.getByLabel("Tên doanh nghiệp").fill("Quán Cơm Nhà Làm");
  await page.getByLabel("Họ và tên").fill("Phạm Thị Hoa");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByRole("combobox", { name: "Ngành" }).click();
  await page.getByRole("option", { name: "Nhà hàng" }).click();
  await expectNoSeriousA11yViolations(page);
  await page.getByRole("button", { name: "Tạo tài khoản" }).click();

  await expect(page).toHaveURL(/\/surveys$/);
  await page.getByRole("button", { name: "Tài khoản" }).click();
  await expect(page.getByRole("menu")).toContainText(email);
  await expect(page.getByRole("menu")).toContainText("Quán Cơm Nhà Làm · Quản trị viên");
});

test("đăng xuất rồi đăng nhập lại, sai mật khẩu báo lỗi tiếng Việt", async ({ page }) => {
  const { email } = await registerViaApi(page);
  await page.goto("/surveys");
  await page.getByRole("button", { name: "Tài khoản" }).click();
  await page.getByRole("menuitem", { name: "Đăng xuất" }).click();
  await expect(page).toHaveURL(/\/login/);

  await page.goto("/surveys");
  await expect(page).toHaveURL(/\/login\?next=/);
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mật khẩu").fill("SaiMatKhau1");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page.locator("form").getByRole("alert")).toContainText(
    "Email hoặc mật khẩu không đúng.",
  );

  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/surveys$/);
});

test("quản trị: tạo/xóa không gian, mời thành viên và người được mời tham gia", async ({
  page,
  browser,
}) => {
  await registerViaApi(page, { company: "Chuỗi Trà Sữa" });
  await page.goto("/admin?tab=workspaces");
  await expect(page.getByRole("heading", { level: 1, name: "Quản lý" })).toBeVisible();

  await page.getByRole("button", { name: "Tạo không gian" }).click();
  await page.getByLabel("Tên không gian").fill("Chi nhánh Gò Vấp");
  await page.getByRole("button", { name: "Lưu" }).click();
  await expect(page.getByRole("heading", { name: "Chi nhánh Gò Vấp" })).toBeVisible();

  // Xóa có xác nhận bằng tên.
  const card = page.getByRole("listitem").filter({ hasText: "Chi nhánh Gò Vấp" });
  await card.getByRole("button", { name: "Xóa" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("button", { name: "Xóa" })).toBeDisabled();
  await dialog.getByLabel(/Nhập “Chi nhánh Gò Vấp”/).fill("Chi nhánh Gò Vấp");
  await dialog.getByRole("button", { name: "Xóa" }).click();
  await expect(page.getByRole("heading", { name: "Chi nhánh Gò Vấp" })).toHaveCount(0);

  // Mời nhân viên phân tích.
  await page.getByRole("tab", { name: "Lời mời" }).click();
  const invitee = uniqueEmail("moi");
  await page.getByLabel("Email").fill(invitee);
  await page.getByRole("button", { name: "Gửi lời mời" }).click();
  const linkInput = page.getByRole("textbox", { name: /gửi trực tiếp liên kết/ });
  await expect(linkInput).toBeVisible();
  const link = await linkInput.inputValue();
  await expect(
    page.getByRole("region", { name: "Lời mời đang chờ" }).getByText(invitee),
  ).toBeVisible();
  await expectNoHorizontalScroll(page);

  // Người được mời mở link trong trình duyệt khác.
  const other = await browser.newContext();
  const guest = await other.newPage();
  await guest.goto(new URL(link).pathname);
  await expect(guest.getByRole("heading", { name: "Lời mời tham gia" })).toBeVisible();
  await expect(guest.getByText("Chuỗi Trà Sữa")).toBeVisible();
  await guest.getByLabel("Họ và tên").fill("Lê Minh Tú");
  await guest.getByLabel("Mật khẩu").fill(PASSWORD);
  await guest.getByRole("button", { name: "Tham gia" }).click();
  await expect(guest).toHaveURL(/\/surveys$/);
  // Nhân viên phân tích không thấy menu Quản lý.
  await expect(guest.getByRole("link", { name: "Quản lý" })).toHaveCount(0);
  await other.close();

  // Admin thấy thành viên mới.
  await page.getByRole("tab", { name: "Thành viên" }).click();
  await expect(page.getByText("Lê Minh Tú")).toBeVisible();
  await expectNoSeriousA11yViolations(page);
});

test("trang cá nhân: đổi tên hiển thị", async ({ page }) => {
  await registerViaApi(page);
  await page.goto("/profile");
  const name = page.getByLabel("Họ và tên");
  await expect(name).toHaveValue("Người Kiểm Thử");
  await name.fill("Tên Đã Đổi");
  await page.getByRole("button", { name: "Lưu" }).first().click();
  await expect(page.getByText("Đã lưu thay đổi")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Họ và tên")).toHaveValue("Tên Đã Đổi");
});
