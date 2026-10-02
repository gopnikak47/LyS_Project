import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { AuthForm } from "@/components/auth/auth-form";
import { renderWithIntl } from "../render";

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

  it("dữ liệu hợp lệ -> hiện thông báo chưa nối API (GĐ 2)", async () => {
    const user = userEvent.setup();
    renderWithIntl(<AuthForm mode="login" />);
    await user.type(screen.getByLabelText("Email"), "an@example.com");
    await user.type(screen.getByLabelText("Mật khẩu"), "matkhau-an-toan");
    await user.click(screen.getByRole("button", { name: "Đăng nhập" }));

    expect(await screen.findByRole("status")).toHaveTextContent("Giai đoạn 2");
  });
});
