import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api/client";

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = "lys_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
});

describe("api client", () => {
  it("gửi header CSRF lấy từ cookie cho request ghi", async () => {
    document.cookie = "lys_csrf=abc123";
    const fetchMock = vi.fn().mockResolvedValue(json(200, { ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    await api("/workspaces", { method: "POST", body: { name: "X" } });
    const init = fetchMock.mock.calls[0]![1];
    expect(init.headers["X-CSRF-Token"]).toBe("abc123");
    expect(init.credentials).toBe("include");
  });

  it("401 → tự refresh một lần rồi thử lại, gộp các request đồng thời", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url.endsWith("/auth/refresh")) return json(200, {});
      const retried = fetchMock.mock.calls.filter(([u]) => u === url).length > 1;
      return retried ? json(200, { url }) : json(401, { error: { code: "UNAUTHORIZED" } });
    });
    vi.stubGlobal("fetch", fetchMock);
    const [a, b] = await Promise.all([api<{ url: string }>("/a"), api<{ url: string }>("/b")]);
    expect(a.url).toBe("/api/v1/a");
    expect(b.url).toBe("/api/v1/b");
    const refreshCalls = fetchMock.mock.calls.filter(([u]) => u.endsWith("/auth/refresh"));
    expect(refreshCalls).toHaveLength(1);
  });

  it("refresh thất bại → ném ApiError 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(json(401, { error: { code: "UNAUTHORIZED", message: "Hết phiên" } })),
    );
    await expect(api("/workspaces")).rejects.toMatchObject({ status: 401, code: "UNAUTHORIZED" });
  });

  it("chuyển lỗi 422 thành map lỗi theo trường", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        json(422, {
          error: {
            code: "VALIDATION_ERROR",
            message: "Dữ liệu không hợp lệ.",
            details: [{ field: "email", message: "Email sai" }],
          },
        }),
      ),
    );
    const error = await api("/auth/register", { method: "POST", body: {} }).catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).fieldErrors()).toEqual({ email: "Email sai" });
  });

  it("lỗi mạng → ApiError NETWORK với thông điệp tiếng Việt", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(api("/workspaces")).rejects.toMatchObject({ code: "NETWORK" });
  });
});
