import { screen } from "@testing-library/react";
import { MessageSquareText, TriangleAlert } from "lucide-react";
import { describe, expect, it } from "vitest";
import { KpiCard } from "@/components/feedback/kpi-card";
import { SentimentBadge, UrgentBadge } from "@/components/feedback/sentiment-badge";
import { StarRating } from "@/components/feedback/star-rating";
import { EmptyState, ErrorState } from "@/components/feedback/states";
import { renderWithIntl } from "../render";

describe("SentimentBadge", () => {
  it.each([
    ["positive", "Tích cực", "bg-positive-soft"],
    ["negative", "Tiêu cực", "bg-negative-soft"],
    ["neutral", "Trung lập", "bg-neutral-soft"],
  ] as const)("hiển thị %s bằng chữ và màu ngữ nghĩa", (sentiment, label, colorClass) => {
    renderWithIntl(<SentimentBadge sentiment={sentiment} />);
    const badge = screen.getByText(label).closest("[data-slot=badge]");
    expect(badge).toHaveClass(colorClass);
    expect(badge).toHaveAttribute("data-sentiment", sentiment);
  });

  it("làm tròn độ tin cậy thành phần trăm", () => {
    renderWithIntl(<SentimentBadge sentiment="positive" confidence={0.876} />);
    expect(screen.getByTitle("Độ tin cậy 88%")).toHaveTextContent("88%");
  });

  it("nhãn khẩn cấp dùng màu cam", () => {
    renderWithIntl(<UrgentBadge />);
    expect(screen.getByText("Khẩn cấp").closest("[data-slot=badge]")).toHaveClass("bg-urgent-soft");
  });
});

describe("KpiCard", () => {
  it("chỉ số tăng là tốt -> màu xanh", () => {
    renderWithIntl(
      <KpiCard label="Tổng phản hồi" value="120" icon={MessageSquareText} delta={12} />,
    );
    expect(screen.getByText("+12%").closest("span")).toHaveClass("bg-positive-soft");
  });

  it("cảnh báo khẩn tăng là xấu -> màu đỏ", () => {
    renderWithIntl(
      <KpiCard
        label="Cảnh báo khẩn"
        value="3"
        icon={TriangleAlert}
        delta={50}
        higherIsBetter={false}
      />,
    );
    expect(screen.getByText("+50%").closest("span")).toHaveClass("bg-negative-soft");
  });
});

describe("StarRating", () => {
  it("có nhãn đọc màn hình bằng tiếng Việt", () => {
    renderWithIntl(<StarRating value={4} />);
    expect(screen.getByRole("img", { name: "4 trên 5 sao" })).toBeInTheDocument();
  });
});

describe("Trạng thái rỗng / lỗi", () => {
  it("EmptyState dùng role=status, ErrorState dùng role=alert", () => {
    renderWithIntl(
      <>
        <EmptyState title="Chưa có dữ liệu" />
        <ErrorState title="Không tải được dữ liệu" />
      </>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Chưa có dữ liệu");
    expect(screen.getByRole("alert")).toHaveTextContent("Không tải được dữ liệu");
  });
});
