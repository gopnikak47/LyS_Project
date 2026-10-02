/**
 * DỮ LIỆU MINH HỌA cho Giai đoạn 0 — chỉ dùng để trình bày bố cục giao diện.
 * Sẽ được thay bằng dữ liệu thật từ API ở các giai đoạn sau. Không dùng cho thống kê.
 */
import type { Sentiment, SurveyStatus } from "@lys/shared";

export type DemoSurvey = {
  id: string;
  name: string;
  status: SurveyStatus;
  responses: number;
  csat: number | null;
  createdAt: string;
  cover: string;
};

export const DEMO_SURVEYS: DemoSurvey[] = [
  {
    id: "s1",
    name: "Khảo sát hài lòng – Chi nhánh Quận 1",
    status: "published",
    responses: 1284,
    csat: 4.3,
    createdAt: "2026-08-12",
    cover: "from-indigo-500 to-sky-400",
  },
  {
    id: "s2",
    name: "Đánh giá món mới mùa thu",
    status: "published",
    responses: 342,
    csat: 4.6,
    createdAt: "2026-09-03",
    cover: "from-amber-400 to-rose-400",
  },
  {
    id: "s3",
    name: "Phản hồi ứng dụng đặt bàn",
    status: "draft",
    responses: 0,
    csat: null,
    createdAt: "2026-09-20",
    cover: "from-emerald-500 to-teal-400",
  },
  {
    id: "s4",
    name: "NPS khách hàng thân thiết Q3",
    status: "closed",
    responses: 917,
    csat: 3.9,
    createdAt: "2026-07-01",
    cover: "from-fuchsia-500 to-violet-500",
  },
];

export type DemoResponse = {
  id: string;
  content: string;
  rating: number;
  sentiment: Sentiment;
  confidence: number;
  topics: { label: string; color: string }[];
  source: string;
  time: string;
  urgent?: boolean;
};

export const DEMO_RESPONSES: DemoResponse[] = [
  {
    id: "r1",
    content: "Ăn xong cả nhà bị đau bụng, đề nghị kiểm tra lại khâu vệ sinh bếp!!",
    rating: 1,
    sentiment: "negative",
    confidence: 0.97,
    topics: [
      { label: "Vệ sinh", color: "oklch(0.6 0.15 200)" },
      { label: "Món ăn", color: "oklch(0.65 0.17 50)" },
    ],
    source: "QR · Bàn 12",
    time: "09:42",
    urgent: true,
  },
  {
    id: "r2",
    content: "Món ăn ngon, nhân viên phục vụ rất nhiệt tình 😍",
    rating: 5,
    sentiment: "positive",
    confidence: 0.95,
    topics: [
      { label: "Món ăn", color: "oklch(0.65 0.17 50)" },
      { label: "Phục vụ", color: "oklch(0.55 0.18 300)" },
    ],
    source: "Link",
    time: "09:15",
  },
  {
    id: "r3",
    content: "Chờ món hơi lâu nhưng ko gian đẹp, giá ok",
    rating: 3,
    sentiment: "neutral",
    confidence: 0.71,
    topics: [
      { label: "Không gian", color: "oklch(0.6 0.13 150)" },
      { label: "Giá cả", color: "oklch(0.55 0.15 260)" },
    ],
    source: "QR · Quầy",
    time: "08:58",
  },
  {
    id: "r4",
    content: "Giá hơi cao so với khẩu phần, nước uống dc",
    rating: 2,
    sentiment: "negative",
    confidence: 0.83,
    topics: [{ label: "Giá cả", color: "oklch(0.55 0.15 260)" }],
    source: "Email",
    time: "Hôm qua",
  },
];
