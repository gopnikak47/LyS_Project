import { NextResponse, type NextRequest } from "next/server";

/**
 * Chặn sớm khu quản trị khi chưa đăng nhập (Next.js 16 "proxy", trước gọi là middleware).
 * Chỉ kiểm tra sự hiện diện cookie phiên — xác thực thật luôn do API đảm nhiệm.
 * Dùng cookie `lys_csrf` (sống cùng refresh token) vì access token ngắn hạn có thể đã hết hạn
 * nhưng vẫn làm mới được.
 */
const PROTECTED = [
  "/surveys",
  "/profile",
  "/billing",
  "/admin",
  "/ui-kit",
  "/reports",
  "/responses",
];

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const needsAuth = PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (needsAuth && !request.cookies.has("lys_csrf")) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|healthz|favicon.ico|icon.svg|robots.txt).*)"],
};
