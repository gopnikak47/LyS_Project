/** Tên ứng dụng — placeholder dễ thay qua biến môi trường `NEXT_PUBLIC_APP_NAME`. */
export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME || "LyS Survey";

/** Viết tắt dùng cho logo tạm (ví dụ "LyS Survey" → "LS"). */
export const APP_INITIALS = APP_NAME.split(/\s+/)
  .filter(Boolean)
  .slice(0, 2)
  .map((word) => word[0]?.toUpperCase() ?? "")
  .join("");
