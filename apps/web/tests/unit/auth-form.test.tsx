import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AuthForm, safeNext } from "@/components/auth/auth-form";
import { renderWithIntl } from "../render";

const replace = vi.fn();
let search = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => search,
  usePathname: () => "/login",
}));

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeEach(() => {
  replace.mockReset();
  search = new URLSearchParams();
});
afterEach(() => vi.unstubAllGlobals());

describe("AuthForm", () => {
  it("báo lỗi validate bằng tiếng Việt khi bỏ trống", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AuthForm mode="register" />);
    await user.click(screen.getByRole("button", { name: "Tạo tài khoản" }));

    expect(await screen.findByText("Email không hợp lệ.")).toBeInTheDocument();
    expect(screen.getByText("Cần tối thiểu 8 ký tự.")).toBeInTheDocument();
    expect(screen.getAllByText("Cần tối thiểu 2 ký tự.")).toHaveLength(2);
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true");
  });

  it("mật khẩu đăng ký phải có cả chữ và số", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AuthForm mode="register" />);
    await user.type(screen.getByLabelText("Mật khẩu"), "chicochuthoi");
    await user.click(screen.getByRole("button", { name: "Tạo tài khoản" }));
    expect(await screen.findByText(/gồm cả chữ và số/)).toBeInTheDocument();
  });

  it("đăng nhập thành công → gọi API và chuyển tới trang tiếp theo", async () => {
    search = new URLSearchParams("next=/admin");
    const fetchMock = mockFetch(200, { user: { full_name: "An" }, permissions: [] });
    const user = userEvent.setup();
    renderWithIntl(<AuthForm mode="login" />);
    await user.type(screen.getByLabelText("Email"), "an@example.com");
    await user.type(screen.getByLabelText("Mật khẩu"), "MatKhau123");
    await user.click(screen.getByRole("button", { name: "Đăng nhập" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/admin"));
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("/api/v1/auth/login");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({ email: "an@example.com", password: "MatKhau123" });
  });

  it("hiển thị thông điệp lỗi từ API", async () => {
    mockFetch(401, {
      error: { code: "INVALID_CREDENTIALS", message: "Email hoặc mật khẩu không đúng." },
    });
    const user = userEvent.setup();
    renderWithIntl(<AuthForm mode="login" />);
    await user.type(screen.getByLabelText("Email"), "an@example.com");
    await user.type(screen.getByLabelText("Mật khẩu"), "sai");
    await user.click(screen.getByRole("button", { name: "Đăng nhập" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email hoặc mật khẩu không đúng.");
    expect(replace).not.toHaveBeenCalled();
  });

  it("chống chuyển hướng ra ngoài qua tham số next", () => {
    expect(safeNext("/admin?tab=members")).toBe("/admin?tab=members");
    expect(safeNext("https://evil.example")).toBe("/surveys");
    expect(safeNext("//evil.example")).toBe("/surveys");
    expect(safeNext(null)).toBe("/surveys");
  });
});
