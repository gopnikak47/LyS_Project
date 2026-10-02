// Kiểm tra mọi file ngôn ngữ có cùng bộ khóa với `vi.json` (ngôn ngữ mặc định).
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const dir = join(dirname(fileURLToPath(import.meta.url)), "..", "i18n");

function flatten(obj, prefix = "") {
  return Object.entries(obj).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return value && typeof value === "object" ? flatten(value, path) : [path];
  });
}

const load = (file) => JSON.parse(readFileSync(join(dir, file), "utf8"));
const base = new Set(flatten(load("vi.json")));
let failed = false;

for (const file of readdirSync(dir).filter((f) => f.endsWith(".json") && f !== "vi.json")) {
  const keys = new Set(flatten(load(file)));
  const missing = [...base].filter((k) => !keys.has(k));
  const extra = [...keys].filter((k) => !base.has(k));
  if (missing.length || extra.length) {
    failed = true;
    console.error(`✗ ${file}: thiếu ${missing.length} khóa, thừa ${extra.length} khóa`);
    missing.forEach((k) => console.error(`  - thiếu: ${k}`));
    extra.forEach((k) => console.error(`  + thừa:  ${k}`));
  } else {
    console.log(`✓ ${file}: khớp ${keys.size} khóa với vi.json`);
  }
}

process.exit(failed ? 1 : 0);
