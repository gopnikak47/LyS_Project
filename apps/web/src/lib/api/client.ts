/**
 * Client gọi API `/api/v1/*`.
 * - Gửi cookie phiên (httpOnly) + header X-CSRF-Token lấy từ cookie `lys_csrf`.
 * - Gặp 401 → tự gọi /auth/refresh MỘT lần (gộp các request đồng thời) rồi thử lại.
 * - Lỗi trả về dạng chuẩn `{error: {code, message, details}}` → ném `ApiError`.
 */

const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "/api").replace(/\/$/, "");
const PREFIX = `${BASE}/v1`;
const NO_REFRESH = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: unknown,
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** Lỗi theo trường (422) → map { tên_trường: thông_điệp } để hiển thị dưới ô nhập. */
  fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.details)) return {};
    return Object.fromEntries(
      (this.details as { field?: string; message?: string }[])
        .filter((d) => d.field)
        .map((d) => [d.field!.split(".").pop()!, d.message ?? ""]),
    );
  }
}

export function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : undefined;
}

type Options = {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  /** Gửi FormData (upload) thay vì JSON. */
  form?: FormData;
};

let refreshing: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  refreshing ??= raw("/auth/refresh", { method: "POST" })
    .then((res) => res.ok)
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

async function raw(path: string, { method = "GET", body, signal, form }: Options = {}) {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const csrf = readCookie("lys_csrf");
  if (csrf && method !== "GET") headers["X-CSRF-Token"] = csrf;
  return fetch(`${PREFIX}${path}`, {
    method,
    headers,
    body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    credentials: "include",
    signal,
  });
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const data = await res.json();
    const err = data?.error ?? {};
    return new ApiError(
      res.status,
      err.code ?? "UNKNOWN",
      err.message ?? "Đã xảy ra lỗi.",
      err.details,
      err.request_id,
    );
  } catch {
    return new ApiError(res.status, "NETWORK", "Không kết nối được máy chủ.");
  }
}

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  let res: Response;
  try {
    res = await raw(path, options);
    if (res.status === 401 && !NO_REFRESH.some((p) => path.startsWith(p))) {
      if (await refreshSession()) res = await raw(path, options);
    }
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(0, "NETWORK", "Không kết nối được máy chủ. Vui lòng kiểm tra mạng.");
  }
  if (!res.ok) throw await toError(res);
  if (res.status === 204) return undefined as T;
  const type = res.headers.get("content-type") ?? "";
  return (type.includes("application/json") ? res.json() : res.blob()) as Promise<T>;
}

/** URL tuyệt đối tới API (dùng cho thẻ <img>, link tải file). */
export function apiUrl(path: string): string {
  return `${PREFIX}${path}`;
}
