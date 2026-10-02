import sentiments from "./sentiments.json";

/** Ngôn ngữ hỗ trợ. `vi` là mặc định. */
export const LOCALES = ["vi", "en"] as const;
export type Locale = (typeof LOCALES)[number];
export const DEFAULT_LOCALE: Locale = "vi";
export const LOCALE_COOKIE = "NEXT_LOCALE";

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

/** Nhãn cảm xúc — khớp `lys_nlp.labels.Sentiment` phía Python. */
export type Sentiment = "positive" | "negative" | "neutral";
export const SENTIMENTS = sentiments.map((s) => s.value) as Sentiment[];

/** Vai trò người dùng trong một doanh nghiệp (tenant). */
export const ROLES = ["SUPER_ADMIN", "ADMIN", "ANALYST", "VIEWER"] as const;
export type Role = (typeof ROLES)[number];

/** Trạng thái vòng đời khảo sát. */
export const SURVEY_STATUSES = ["draft", "published", "closed", "archived"] as const;
export type SurveyStatus = (typeof SURVEY_STATUSES)[number];

/** Ngành có bộ chủ đề mẫu (FR-12). */
export const INDUSTRIES = [
  "restaurant",
  "it",
  "hotel",
  "retail",
  "education",
  "healthcare",
] as const;
export type Industry = (typeof INDUSTRIES)[number];
