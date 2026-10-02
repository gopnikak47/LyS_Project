"""Bộ chủ đề mẫu theo ngành (FR-12).

Mô tả và từ khóa được dùng làm "prototype" cho phân loại chủ đề zero-shot (FR-16),
nên viết ngắn gọn, đúng cách khách hàng Việt Nam hay diễn đạt (kể cả viết tắt).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TopicTemplate:
    name: str
    description: str
    keywords: tuple[str, ...]
    color: str


@dataclass(frozen=True, slots=True)
class IndustryTemplate:
    code: str
    name: str
    topics: tuple[TopicTemplate, ...] = field(default_factory=tuple)


def _t(name: str, description: str, keywords: str, color: str) -> TopicTemplate:
    return TopicTemplate(name, description, tuple(k.strip() for k in keywords.split(",")), color)


INDUSTRY_TEMPLATES: dict[str, IndustryTemplate] = {
    "restaurant": IndustryTemplate(
        "restaurant",
        "Nhà hàng",
        (
            _t(
                "Món ăn",
                "Chất lượng, hương vị, độ tươi, khẩu phần và trình bày món ăn, đồ uống",
                "món ăn, đồ ăn, ngon, dở, nhạt, mặn, tươi, nguội, khẩu phần, nước uống, nêm nếm",
                "#f97316",
            ),
            _t(
                "Phục vụ",
                "Thái độ, tốc độ và sự chuyên nghiệp của nhân viên phục vụ",
                "nhân viên, phục vụ, thái độ, nhiệt tình, chờ, lâu, chậm, order, tư vấn",
                "#8b5cf6",
            ),
            _t(
                "Giá cả",
                "Mức giá, khuyến mãi, hóa đơn và cảm nhận về giá trị so với chi phí",
                "giá, đắt, rẻ, hợp lý, tiền, hóa đơn, khuyến mãi, voucher, tính tiền",
                "#0ea5e9",
            ),
            _t(
                "Không gian",
                "Không gian, chỗ ngồi, âm nhạc, ánh sáng, bãi đỗ xe",
                "không gian, chỗ ngồi, ồn, nhạc, thoáng, đẹp, view, chật, chỗ để xe",
                "#22c55e",
            ),
            _t(
                "Vệ sinh",
                "Độ sạch sẽ của bàn ghế, dụng cụ, nhà vệ sinh và an toàn thực phẩm",
                "vệ sinh, sạch, bẩn, ruồi, gián, tóc, mùi hôi, toilet, đau bụng, ngộ độc",
                "#14b8a6",
            ),
        ),
    ),
    "it": IndustryTemplate(
        "it",
        "Công nghệ thông tin",
        (
            _t(
                "Giao diện",
                "Thiết kế, bố cục, màu sắc và mức độ dễ sử dụng của ứng dụng",
                "giao diện, UI, đẹp, rối, khó dùng, dễ dùng, font, màu, bố cục",
                "#6366f1",
            ),
            _t(
                "Tính năng",
                "Chức năng hiện có, yêu cầu tính năng mới và mức độ đáp ứng nhu cầu",
                "tính năng, chức năng, thêm, thiếu, cần có, đề xuất, tiện, hữu ích",
                "#0ea5e9",
            ),
            _t(
                "Hiệu năng",
                "Tốc độ tải, độ mượt, thời gian phản hồi, tiêu thụ pin và dung lượng",
                "chậm, nhanh, lag, giật, load, tải, mượt, tốn pin, nặng",
                "#f59e0b",
            ),
            _t(
                "Lỗi hệ thống",
                "Lỗi, treo, văng ứng dụng, mất dữ liệu, không đăng nhập hoặc thanh toán được",
                "lỗi, bug, crash, văng, treo, không vào được, mất dữ liệu, đăng nhập, thanh toán",
                "#ef4444",
            ),
            _t(
                "Hỗ trợ",
                "Chăm sóc khách hàng, tổng đài, phản hồi yêu cầu hỗ trợ và hướng dẫn",
                "hỗ trợ, tổng đài, CSKH, phản hồi, hotline, chat, hướng dẫn, gọi",
                "#22c55e",
            ),
        ),
    ),
    "hotel": IndustryTemplate(
        "hotel",
        "Khách sạn",
        (
            _t(
                "Phòng ở",
                "Tiện nghi, giường, độ sạch và trang thiết bị trong phòng",
                "phòng, giường, chăn, điều hòa, máy lạnh, view, rộng, chật, cách âm",
                "#6366f1",
            ),
            _t(
                "Lễ tân",
                "Thủ tục nhận/trả phòng và thái độ của nhân viên lễ tân",
                "lễ tân, check-in, check-out, nhận phòng, trả phòng, nhân viên, đón",
                "#8b5cf6",
            ),
            _t(
                "Vệ sinh",
                "Độ sạch sẽ của phòng, phòng tắm, khăn và khu vực chung",
                "sạch, bẩn, khăn, toilet, phòng tắm, mùi, dọn phòng, côn trùng",
                "#14b8a6",
            ),
            _t(
                "Ẩm thực",
                "Bữa sáng, nhà hàng và dịch vụ ăn uống của khách sạn",
                "bữa sáng, buffet, đồ ăn, nhà hàng, món, đồ uống",
                "#f97316",
            ),
            _t(
                "Vị trí & tiện ích",
                "Vị trí, hồ bơi, gym, spa, bãi đỗ xe và tiện ích chung",
                "vị trí, gần biển, hồ bơi, gym, spa, bãi xe, wifi, thang máy",
                "#22c55e",
            ),
            _t(
                "Giá cả",
                "Giá phòng, phụ phí và chính sách hoàn hủy",
                "giá, đắt, rẻ, phụ phí, hoàn tiền, hủy phòng, khuyến mãi",
                "#0ea5e9",
            ),
        ),
    ),
    "retail": IndustryTemplate(
        "retail",
        "Bán lẻ",
        (
            _t(
                "Sản phẩm",
                "Chất lượng, hạn dùng, nguồn gốc và sự đa dạng của hàng hóa",
                "sản phẩm, hàng, chất lượng, hết hạn, date, nguồn gốc, đa dạng, hết hàng",
                "#f97316",
            ),
            _t(
                "Nhân viên",
                "Thái độ và sự hỗ trợ của nhân viên bán hàng, thu ngân",
                "nhân viên, thu ngân, tư vấn, thái độ, nhiệt tình",
                "#8b5cf6",
            ),
            _t(
                "Thanh toán",
                "Thời gian chờ thanh toán, phương thức thanh toán, hóa đơn",
                "thanh toán, xếp hàng, quầy, chờ, thẻ, QR, hóa đơn, tính tiền",
                "#0ea5e9",
            ),
            _t(
                "Giá & khuyến mãi",
                "Giá bán, chương trình khuyến mãi, tích điểm",
                "giá, khuyến mãi, giảm giá, tích điểm, voucher, đắt, rẻ",
                "#eab308",
            ),
            _t(
                "Cửa hàng",
                "Bố trí, sạch sẽ, bãi giữ xe và giờ mở cửa",
                "cửa hàng, siêu thị, kệ, sạch, chật, giữ xe, giờ mở cửa",
                "#22c55e",
            ),
            _t(
                "Giao hàng",
                "Tốc độ, đóng gói và tình trạng hàng khi giao",
                "giao hàng, ship, đóng gói, móp, vỡ, trễ, shipper",
                "#ef4444",
            ),
        ),
    ),
    "education": IndustryTemplate(
        "education",
        "Giáo dục",
        (
            _t(
                "Giảng viên",
                "Phương pháp giảng dạy, kiến thức và sự nhiệt tình của giảng viên",
                "giảng viên, thầy, cô, dạy, giảng, nhiệt tình, dễ hiểu, khó hiểu",
                "#6366f1",
            ),
            _t(
                "Chương trình học",
                "Nội dung, giáo trình, độ khó và tính thực tiễn của môn học",
                "giáo trình, nội dung, chương trình, bài tập, thực hành, lý thuyết, khó",
                "#0ea5e9",
            ),
            _t(
                "Cơ sở vật chất",
                "Phòng học, thiết bị, thư viện, wifi",
                "phòng học, máy chiếu, điều hòa, thư viện, wifi, bàn ghế, cơ sở vật chất",
                "#22c55e",
            ),
            _t(
                "Đánh giá & thi cử",
                "Kiểm tra, chấm điểm, đề thi và sự công bằng",
                "thi, kiểm tra, điểm, chấm, đề, công bằng",
                "#f59e0b",
            ),
            _t(
                "Học phí & thủ tục",
                "Học phí, thủ tục hành chính, hỗ trợ sinh viên",
                "học phí, thủ tục, đăng ký, giáo vụ, hỗ trợ",
                "#ef4444",
            ),
        ),
    ),
    "healthcare": IndustryTemplate(
        "healthcare",
        "Y tế",
        (
            _t(
                "Bác sĩ",
                "Chuyên môn, sự tận tâm và cách tư vấn của bác sĩ",
                "bác sĩ, khám, chẩn đoán, tư vấn, tận tâm, chuyên môn",
                "#6366f1",
            ),
            _t(
                "Điều dưỡng",
                "Thái độ, sự chăm sóc của điều dưỡng và nhân viên y tế",
                "điều dưỡng, y tá, chăm sóc, tiêm, nhân viên, thái độ",
                "#8b5cf6",
            ),
            _t(
                "Thời gian chờ",
                "Thời gian chờ khám, chờ kết quả, quy trình tiếp đón",
                "chờ, lâu, xếp hàng, số thứ tự, kết quả, tiếp đón, quy trình",
                "#f59e0b",
            ),
            _t(
                "Cơ sở vật chất",
                "Phòng bệnh, trang thiết bị, vệ sinh bệnh viện",
                "phòng bệnh, giường, máy móc, thiết bị, vệ sinh, sạch, chật",
                "#14b8a6",
            ),
            _t(
                "Chi phí & bảo hiểm",
                "Viện phí, thuốc, thanh toán bảo hiểm y tế",
                "viện phí, chi phí, thuốc, bảo hiểm, BHYT, thanh toán, đắt",
                "#0ea5e9",
            ),
        ),
    ),
}
