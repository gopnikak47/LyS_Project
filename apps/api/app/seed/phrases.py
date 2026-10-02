"""Kho câu nhận xét tiếng Việt để sinh DỮ LIỆU MINH HỌA (không phải dữ liệu khách hàng thật).

Mỗi câu gắn với chủ đề (theo tên trong bộ chủ đề mẫu) và sắc thái. Bộ sinh sẽ ghép 1–3 câu,
thêm biến thể viết tắt/teencode, emoji, lặp ký tự… để giống phản hồi thực tế.
"""

from __future__ import annotations

# (chủ đề, câu)
PHRASES: dict[str, dict[str, list[tuple[str, str]]]] = {
    "restaurant": {
        "positive": [
            ("Món ăn", "Món ăn rất ngon, nêm nếm vừa miệng"),
            ("Món ăn", "Đồ ăn tươi, lên món đẹp mắt"),
            ("Món ăn", "Phở ở đây ngon nhất khu này"),
            ("Món ăn", "Nước dùng đậm đà, thịt mềm"),
            ("Món ăn", "Món mới mùa thu rất hợp khẩu vị cả nhà"),
            ("Phục vụ", "Nhân viên phục vụ rất nhiệt tình, chu đáo"),
            ("Phục vụ", "Bạn nhân viên tư vấn món rất dễ thương"),
            ("Phục vụ", "Lên món nhanh, gọi là có ngay"),
            ("Giá cả", "Giá cả hợp lý so với chất lượng"),
            ("Giá cả", "Có voucher giảm giá nên rất đáng tiền"),
            ("Không gian", "Không gian thoáng mát, decor đẹp"),
            ("Không gian", "Quán yên tĩnh, hợp đi gia đình"),
            ("Vệ sinh", "Bàn ghế sạch sẽ, nhà vệ sinh thơm tho"),
        ],
        "negative": [
            ("Món ăn", "Món ăn bị nguội, không ngon như lần trước"),
            ("Món ăn", "Canh quá mặn, cơm thì khô"),
            ("Món ăn", "Khẩu phần ít quá, ăn không no"),
            ("Phục vụ", "Chờ món quá lâu, gần 40 phút mới có"),
            ("Phục vụ", "Nhân viên thái độ không tốt, gọi mãi không ai ra"),
            ("Phục vụ", "Mang nhầm món mà không xin lỗi"),
            ("Giá cả", "Giá hơi đắt so với chất lượng"),
            ("Giá cả", "Tính tiền sai, phải kiểm tra lại hóa đơn"),
            ("Không gian", "Quán ồn ào, nhạc mở quá to"),
            ("Không gian", "Không có chỗ để xe, phải gửi xa"),
            ("Vệ sinh", "Bàn còn bẩn, có ruồi bay xung quanh"),
            ("Vệ sinh", "Nhà vệ sinh hôi, không có giấy"),
        ],
        "neutral": [
            ("Món ăn", "Món ăn bình thường, không có gì đặc biệt"),
            ("Phục vụ", "Phục vụ tạm được"),
            ("Giá cả", "Giá cũng tương đương các quán khác"),
            ("Không gian", "Không gian ổn"),
            ("", "Lần đầu đến ăn thử"),
            ("", "Đi ăn trưa với đồng nghiệp"),
        ],
        "urgent": [
            ("Vệ sinh", "Ăn xong cả nhà bị đau bụng, tiêu chảy cả đêm"),
            ("Vệ sinh", "Phát hiện con gián trong tô canh, quá kinh khủng"),
            ("Món ăn", "Có sợi tóc và dị vật trong món ăn"),
            ("Vệ sinh", "Nghi bị ngộ độc thực phẩm sau khi ăn ở đây"),
            ("Phục vụ", "Nhân viên quát khách, tôi sẽ báo lên báo đài"),
            ("Giá cả", "Tính tiền gian lận, đây là lừa đảo, tôi sẽ kiện"),
        ],
    },
    "hotel": {
        "positive": [
            ("Phòng ở", "Phòng rộng, view biển rất đẹp"),
            ("Phòng ở", "Giường êm, điều hòa mát"),
            ("Lễ tân", "Lễ tân thân thiện, check-in nhanh"),
            ("Vệ sinh", "Phòng sạch sẽ, khăn tắm thơm"),
            ("Ẩm thực", "Buffet sáng phong phú, ngon"),
            ("Vị trí & tiện ích", "Hồ bơi đẹp, gần biển"),
            ("Giá cả", "Giá phòng hợp lý mùa thấp điểm"),
        ],
        "negative": [
            ("Phòng ở", "Phòng cách âm kém, ồn cả đêm"),
            ("Phòng ở", "Điều hòa hỏng, gọi mãi không ai sửa"),
            ("Lễ tân", "Check-in phải chờ hơn một tiếng"),
            ("Vệ sinh", "Phòng tắm có mùi, khăn không sạch"),
            ("Ẩm thực", "Bữa sáng ít món, hết đồ sớm"),
            ("Vị trí & tiện ích", "Wifi rất yếu, thang máy hay hỏng"),
            ("Giá cả", "Phụ phí nhiều, không báo trước"),
        ],
        "neutral": [
            ("Phòng ở", "Phòng ổn so với giá"),
            ("", "Ở 2 đêm công tác"),
            ("Ẩm thực", "Bữa sáng bình thường"),
        ],
        "urgent": [
            ("Vệ sinh", "Phát hiện rệp trên giường, bị cắn khắp người"),
            ("Phòng ở", "Mất đồ trong phòng, tôi sẽ báo công an"),
            ("Ẩm thực", "Ăn buffet xong bị ngộ độc, phải đi viện"),
        ],
    },
    "it": {
        "positive": [
            ("Giao diện", "Giao diện đẹp, dễ dùng"),
            ("Tính năng", "Tính năng đặt lịch rất tiện"),
            ("Hiệu năng", "App chạy mượt, mở nhanh"),
            ("Hỗ trợ", "Tổng đài hỗ trợ nhanh, nhiệt tình"),
            ("Tính năng", "Thanh toán QR tiện lợi"),
        ],
        "negative": [
            ("Giao diện", "Giao diện rối, khó tìm chức năng"),
            ("Hiệu năng", "App load chậm, hay bị lag"),
            ("Lỗi hệ thống", "Hay bị văng app khi thanh toán"),
            ("Lỗi hệ thống", "Không đăng nhập được từ hôm qua"),
            ("Hỗ trợ", "Gọi hotline không ai nghe máy"),
            ("Tính năng", "Thiếu tính năng hủy lịch"),
            ("Hiệu năng", "Tốn pin quá"),
        ],
        "neutral": [
            ("Tính năng", "Mong có thêm chế độ tối"),
            ("", "Mới cài app được vài ngày"),
            ("Giao diện", "Giao diện tạm ổn"),
        ],
        "urgent": [
            ("Lỗi hệ thống", "Bị trừ tiền 2 lần mà không đặt được lịch, đây là lừa đảo"),
            ("Lỗi hệ thống", "Tài khoản bị mất dữ liệu, tôi sẽ kiện công ty"),
        ],
    },
}

EMOJIS = {
    "positive": ["😍", "👍", "❤️", "🥰", "😋", "👏"],
    "negative": ["😡", "👎", "😤", "😞", "🤬"],
    "neutral": ["🙂", "😐", ""],
    "urgent": ["😡", "🤢", "‼️"],
}

# Biến đổi kiểu teencode/viết tắt phổ biến (áp dụng ngẫu nhiên).
TEENCODE = [
    ("không", "ko"),
    ("không", "k"),
    ("được", "dc"),
    ("được", "đc"),
    ("quá", "wá"),
    ("với", "vs"),
    ("rồi", "r"),
    ("nhiều", "nhìu"),
    ("biết", "bít"),
    ("vậy", "v"),
    ("gì", "j"),
    ("ngon", "ngonnnn"),
    ("rất", "rấttt"),
    ("nhân viên", "nv"),
    ("khách hàng", "kh"),
]

# Câu ngắn kiểu "chung chung" đi kèm cho tự nhiên hơn.
CLOSINGS = {
    "positive": ["Sẽ quay lại!", "Recommend cho mọi người", "10 điểm", "Rất hài lòng"],
    "negative": ["Thất vọng", "Không quay lại nữa", "Cần cải thiện", "Hơi buồn"],
    "neutral": ["", "Tạm được", "Cũng ok"],
    "urgent": ["Yêu cầu quản lý liên hệ gấp", "Cần giải quyết ngay", ""],
}

CUSTOMER_NAMES = [
    "Nguyễn Văn An",
    "Trần Thị Bích",
    "Lê Hoàng Long",
    "Phạm Minh Châu",
    "Hoàng Thu Trang",
    "Vũ Đức Huy",
    "Đặng Ngọc Lan",
    "Bùi Quốc Bảo",
    "Đỗ Khánh Linh",
    "Ngô Gia Hân",
]
