"""
attendance.py — Điểm danh real-time qua webcam
===============================================
Module xử lý vòng lặp điểm danh:
  - Nhận diện khuôn mặt liên tục từ camera
  - Chống điểm danh lặp (cooldown)
  - Ghi kết quả vào file CSV theo từng phiên
  - Hỗ trợ hiển thị phân tích cảm xúc/tuổi/giới tính

Chạy độc lập:
    python attendance.py
    python attendance.py ToanA1_Buoi3
    python attendance.py ToanA1_Buoi3 --analysis
"""

import cv2
import csv
import sys
from datetime import datetime, date
from pathlib import Path

from config import (
    ATTENDANCE_PATH, COOLDOWN_SEC,
    COLOR_SUCCESS, COLOR_UNKNOWN, COLOR_INFO,
)
from database import init_directories, load_members
from face_detector import (
    recognize_faces, analyze_face_from_roi,
    draw_face_box, draw_header, draw_footer,
)


# ============================================================
# HÀM ĐIỂM DANH CHÍNH
# ============================================================
def run_attendance(session_name: str = None,
                   show_analysis: bool = False,
                   on_checkin=None) -> dict:
    """
    Chạy vòng lặp điểm danh real-time.

    Args:
        session_name  : Tên phiên (mặc định = ngày hôm nay YYYY-MM-DD)
        show_analysis : True → hiện thêm cảm xúc/tuổi/giới tính
        on_checkin    : Callback gọi khi có người điểm danh thành công.
                        Signature: on_checkin(member_id, name, time_str)

    Returns:
        dict {member_id: time_str} — danh sách đã điểm danh trong phiên
    """
    init_directories()
    members = load_members()

    if not members:
        print("[LOI] Chua co thanh vien nao. Chay register.py truoc.")
        return {}

    # --- Thiết lập phiên ---
    if not session_name:
        session_name = date.today().strftime("%Y-%m-%d")

    csv_file   = ATTENDANCE_PATH / f"{session_name}.csv"
    attended   = _load_existing_attendance(csv_file)  # Nạp lại nếu đã có
    last_seen  = {}   # {member_id: datetime} — chống điểm danh lặp

    # --- Kiểm tra & sửa header CSV trước khi mở append ---
    _ensure_csv_header(csv_file)

    # --- Mở file CSV ---
    csv_fh = open(csv_file, "a", newline="", encoding="utf-8")
    writer = csv.writer(csv_fh)

    # --- Mở webcam ---
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    # cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("[LOI] Khong mo duoc webcam.")
        csv_fh.close()
        return attended

    print(f"\n[*] Bat dau diem danh | Phien: {session_name}")
    print(f"    Co {len(members)} thanh vien | {len(attended)} da diem danh truoc do")
    print("    Nhan Q de ket thuc.\n")

    status_msg   = "San sang nhan dien..."
    status_color = COLOR_INFO
    frame_idx    = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        display    = frame.copy()

        # --- Nhận diện mỗi 15 frame (~2 lần/giây) ---
        if frame_idx % 30 == 0:
            matches = recognize_faces(frame)

            if matches:
                for match in matches:
                    mid        = match["member_id"]
                    conf       = match["confidence"]
                    x1, y1     = match["x1"], match["y1"]
                    x2, y2     = match["x2"], match["y2"]
                    member     = members.get(mid, {})
                    name       = member.get("name", mid)
                    now        = datetime.now()

                    # Kiểm tra cooldown
                    if _in_cooldown(mid, last_seen, now):
                        continue
                    last_seen[mid] = now

                    # Ghi điểm danh mới
                    if mid not in attended:
                        time_str = now.strftime("%H:%M:%S")
                        writer.writerow([mid, name, time_str, session_name])
                        csv_fh.flush()
                        attended[mid] = time_str

                        status_msg   = f"DIEM DANH: {name}  ({time_str})"
                        status_color = COLOR_SUCCESS
                        print(f"  [✓] {name:<25} {mid:<12}  {time_str}")

                        if on_checkin:
                            on_checkin(mid, name, time_str)
                    else:
                        status_msg   = f"{name} da diem danh: {attended[mid]}"
                        status_color = COLOR_INFO

                    # Phân tích cảm xúc tuỳ chọn
                    analysis = None
                    if show_analysis:
                        analysis = analyze_face_from_roi(frame, x1, y1, x2, y2)

                    draw_face_box(display, x1, y1, x2, y2,
                                  label=f"{name}  {conf}%",
                                  color=COLOR_SUCCESS,
                                  analysis=analysis)
            else:
                status_msg   = "Dang tim khuon mat..."
                status_color = COLOR_UNKNOWN

        # --- Vẽ giao diện ---
        draw_header(display, f"DIEM DANH TU DONG  |  Phien: {session_name}")
        draw_footer(display, status_msg, status_color, len(attended))

        cv2.imshow("He Thong Diem Danh — Nhan Q de thoat", display)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # --- Kết thúc ---
    cap.release()
    cv2.destroyAllWindows()
    csv_fh.close()

    print(f"\n[OK] Ket thuc phien: {session_name}")
    print(f"     Tong diem danh : {len(attended)}/{len(members)} nguoi")
    print(f"     File luu       : {csv_file}\n")

    return attended


# ============================================================
# HÀM HỖ TRỢ NỘI BỘ
# ============================================================
def _ensure_csv_header(csv_file: Path):
    """
    Đảm bảo file CSV có header đúng với 4 cột: member_id, name, time, session.
    - Nếu file chưa tồn tại hoặc rỗng → tạo mới với header.
    - Nếu file cũ chỉ có header 2 cột (member_id, name) → migrate sang 4 cột.
    """
    HEADER = ["member_id", "name", "time", "session"]

    if not csv_file.exists() or csv_file.stat().st_size == 0:
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(HEADER)
        return

    # Đọc header hiện tại
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            existing_header = next(reader)
        except StopIteration:
            existing_header = []

    # Nếu đã có đủ cột time → không cần làm gì
    if "time" in existing_header or "Time" in existing_header:
        return

    # Header cũ thiếu cột time → migrate: đọc toàn bộ, ghi lại với header mới
    print(f"[migrate] File CSV cu thieu cot 'time', dang tu dong sua: {csv_file.name}")
    with open(csv_file, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for row in rows:
            writer.writerow([
                row.get("member_id", ""),
                row.get("name", ""),
                row.get("time") or row.get("Time") or row.get("time_str") or "N/A",
                row.get("session", ""),
            ])
    print(f"[migrate] Xong. Da sua {len(rows)} ban ghi.")


def _load_existing_attendance(csv_file: Path) -> dict:
    """Nạp lại bản ghi từ file CSV nếu đã tồn tại (tiếp tục phiên cũ)."""
    attended = {}
    if csv_file.exists():
        with open(csv_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                attended[row.get("member_id")] = row.get("time") or row.get("Time") or "N/A"
    return attended


def _in_cooldown(member_id: str, last_seen: dict, now: datetime) -> bool:
    """Kiểm tra xem thành viên có đang trong thời gian cooldown không."""
    if member_id not in last_seen:
        return False
    elapsed = (now - last_seen[member_id]).total_seconds()
    return elapsed < COOLDOWN_SEC


# ============================================================
# CHẠY ĐỘC LẬP
# ============================================================
if __name__ == "__main__":
    session  = None
    analysis = False

    for arg in sys.argv[1:]:
        if arg == "--analysis":
            analysis = True
        elif not arg.startswith("--"):
            session = arg

    result = run_attendance(session_name=session, show_analysis=analysis)

    if result:
        print("Danh sach da diem danh:")
        for mid, t in result.items():
            print(f"  {mid}: {t}")