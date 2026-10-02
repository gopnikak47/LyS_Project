export type Choice = { value: string; label: Record<string, string>; image_url?: string | null; display_if?: {question?:string;operator?:string;value?:unknown} };
export type Question = {
  id: string; code: string;
  type: "rating" | "csat" | "text" | "single_choice" | "multi_choice" | "nps" | "picture_choice" | "slider" | "ranking" | "contact" | "upload" | "matrix" | "datetime";
  title: Record<string, string>; description: Record<string, string>;
  required: boolean; options: Choice[];
  config: Record<string, unknown>; logic: Record<string, unknown>;
  points?:number|null;
};
export type Theme = {
  primary: string; background: string; text: string;
  font: "sans-serif" | "serif"; font_size: number;
  layout: "scroll" | "one_per_page";
  logo_url?:string|null; background_image?:string|null;
};
export type Survey = {
  id: string; workspace_id: string; title: string; description: string | null;
  slug: string; status: "draft" | "published" | "closed" | "archived";
  response_count: number; updated_at: string; current_version_id: string | null;
  theme: Theme; settings: Record<string, unknown>; questions: Question[];
  languages: string[]; default_language: string; opens_at: string | null; closes_at: string | null;
  is_quiz:boolean;
};
export type Page<T> = { items: T[]; total: number; page: number; page_size: number };
