import { describe, expect, it } from "vitest";
import en from "@lys/shared/i18n/en.json";
import vi from "@lys/shared/i18n/vi.json";

type Tree = { [key: string]: string | Tree };

function flatten(tree: Tree, prefix = ""): Record<string, string> {
  return Object.entries(tree).reduce<Record<string, string>>((acc, [key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") acc[path] = value;
    else Object.assign(acc, flatten(value, path));
    return acc;
  }, {});
}

// Lấy tên biến ICU ở cấp ngoài cùng, ví dụ "{count, plural, ...}" -> "count".
function placeholders(message: string): string[] {
  return [...message.matchAll(/\{\s*([a-zA-Z]+)\s*[,}]/g)].map((m) => m[1]!).sort();
}

const viFlat = flatten(vi as Tree);
const enFlat = flatten(en as Tree);

describe("i18n messages", () => {
  it("vi và en có cùng bộ khóa", () => {
    expect(Object.keys(enFlat).sort()).toEqual(Object.keys(viFlat).sort());
  });

  it("không có chuỗi rỗng", () => {
    for (const [key, value] of Object.entries(viFlat)) {
      expect(value.trim(), key).not.toBe("");
    }
  });

  it("biến nội suy giống nhau giữa các ngôn ngữ", () => {
    for (const key of Object.keys(viFlat)) {
      expect(placeholders(enFlat[key]!), key).toEqual(placeholders(viFlat[key]!));
    }
  });

  it("nhãn cảm xúc tiếng Việt đúng quy ước", () => {
    expect(vi.sentiment).toMatchObject({
      positive: "Tích cực",
      negative: "Tiêu cực",
      neutral: "Trung lập",
      urgent: "Khẩn cấp",
    });
  });
});
