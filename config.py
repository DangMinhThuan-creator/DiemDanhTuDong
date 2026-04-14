"""
config.py — Cấu hình toàn hệ thống điểm danh
=============================================
Chỉnh sửa file này để thay đổi đường dẫn, model AI,
ngưỡng nhận diện và màu sắc hiển thị.
"""

from pathlib import Path

# ============================================================
# ĐƯỜNG DẪN THƯ MỤC
# ============================================================
BASE_DIR        = Path(__file__).parent
DB_PATH         = BASE_DIR / "face_database"       # Ảnh khuôn mặt đã đăng ký
ATTENDANCE_PATH = BASE_DIR / "attendance_records"  # File CSV điểm danh
MEMBERS_FILE    = BASE_DIR / "members.json"        # Thông tin thành viên

# ============================================================
# CẤU HÌNH MODEL AI (DeepFace)
# ============================================================
# Model nhận diện khuôn mặt:
#   VGG-Face   — phổ biến, nhanh, RAM ~600MB
#   Facenet512 — cân bằng tốt nhất, RAM ~90MB  ← khuyến nghị
#   ArcFace    — chính xác nhất, chậm hơn
#   DeepFace   — nhẹ, nhanh
MODEL_NAME = "Facenet512"

# Bộ phát hiện khuôn mặt:
#   opencv     — nhanh nhất, đủ dùng
#   retinaface — chính xác nhất, chậm hơn
#   mtcnn      — cân bằng
DETECTOR = "opencv"

# Độ đo khoảng cách:
#   cosine        — khuyến nghị cho Facenet512
#   euclidean_l2  — lựa chọn thay thế
DISTANCE_METRIC = "cosine"

# Ngưỡng nhận diện (0.0 – 1.0):
#   Giá trị thấp hơn = chặt hơn, ít nhầm hơn nhưng dễ bỏ sót
#   Giá trị cao hơn  = dễ nhận hơn, có thể nhầm người
THRESHOLD = 0.68

# Thời gian chờ giữa 2 lần điểm danh cùng 1 người (giây)
COOLDOWN_SEC = 5

# Số ảnh chụp khi đăng ký qua webcam
DEFAULT_CAPTURE_COUNT = 5

# ============================================================
# MÀU SẮC HIỂN THỊ TRÊN CAMERA (BGR)
# ============================================================
COLOR_SUCCESS = (0, 220, 60)    # Xanh lá — nhận diện thành công
COLOR_UNKNOWN = (0, 60, 220)    # Đỏ      — không nhận ra
COLOR_ERROR   = (30, 30, 220)   # Đỏ đậm  — lỗi
COLOR_INFO    = (220, 200, 0)   # Vàng    — thông tin

# ============================================================
# MÀU SẮC GIAO DIỆN ĐỒ HỌA (Hex)
# ============================================================
BG_DARK   = "#0f1117"
BG_CARD   = "#1a1d27"
BG_PANEL  = "#22263a"
ACCENT    = "#4f8ef7"
SUCCESS   = "#3ecf8e"
WARNING   = "#f6c843"
DANGER    = "#f75f5f"
TEXT_MAIN = "#e8eaf0"
TEXT_MUTE = "#7a7f9a"

# ============================================================
# FONT CHỮ GIAO DIỆN
# ============================================================
FONT_HEAD = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 11)
FONT_MONO = ("Consolas", 10)