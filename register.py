"""
register.py — Đăng ký khuôn mặt thành viên mới
================================================
Hỗ trợ 3 cách đăng ký:
  1. Webcam  — tự động chụp nhiều ảnh từ nhiều góc
  2. File    — copy 1 ảnh sẵn có vào database
  3. Nhiều file — copy danh sách ảnh vào database

Chạy độc lập:
    python register.py                  → hướng dẫn
    python register.py SV001 "Ten"      → đăng ký qua webcam
    python register.py SV001 "Ten" anh.jpg  → đăng ký từ file
"""

import cv2
import shutil
import sys
import time
from pathlib import Path

from config import (
    DB_PATH, DEFAULT_CAPTURE_COUNT,
    COLOR_SUCCESS, COLOR_INFO,
)
from database import (
    init_directories, load_members,
    add_member, delete_member, list_members,
)
from face_detector import draw_header


# ============================================================
# ĐĂNG KÝ TỪ WEBCAM (TỰ ĐỘNG CHỤP)
# ============================================================
def register_from_webcam(member_id: str, name: str,
                         num_captures: int = 200) -> bool:  # CHANGED: 200 ảnh
    """
    Mở webcam và tự động chụp ảnh khuôn mặt để đăng ký.

    Tính năng mới:
      - Tự động chụp liên tục khi phát hiện 1 khuôn mặt
      - Dừng ngay khi phát hiện khuôn mặt thứ 2
      - Giới hạn tối đa 200 ảnh
      - Nhấn Q để dừng bất cứ lúc nào

    Args:
        member_id   : Mã thành viên (VD: "SV001")
        name        : Họ và tên
        num_captures: Số ảnh tối đa (mặc định 200)

    Returns:
        True nếu đăng ký thành công (lưu được ít nhất 1 ảnh).
    """
    init_directories()

    member_dir = DB_PATH / member_id
    member_dir.mkdir(exist_ok=True)

    print(f"\n[*] Dang ky khuon mat: {name}  (ID: {member_id})")
    print(f"    Tu dong chup toi da {num_captures} anh")
    print("    Hay nhin vao camera va xoay dau nhe sang cac huong khac nhau")
    print("    SE DUNG neu phat hien khuon mat thu 2!")
    print("    Q: dung truoc\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[LOI] Khong mo duoc webcam.")
        return False

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    saved = 0
    last_capture_time = 0
    capture_interval = 0.1  # CHANGED: Chụp mỗi 0.1 giây (10 ảnh/giây)

    while saved < num_captures:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces   = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

        # CHANGED: Kiểm tra số lượng khuôn mặt
        num_faces = len(faces)
        
        # Vẽ khung cho tất cả khuôn mặt
        for (x, y, w, h) in faces:
            # Khuôn mặt đầu tiên: màu xanh (OK)
            # Khuôn mặt thứ 2 trở đi: màu đỏ (CẢNH BÁO)
            color = COLOR_SUCCESS if len(faces) == 1 else (0, 0, 255)
            cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)

        # CHANGED: Cảnh báo nếu phát hiện nhiều hơn 1 khuôn mặt
        if num_faces > 1:
            cap.release()
            cv2.destroyAllWindows()
            print(f"\n[!] DUNG! Phat hien {num_faces} khuon mat trong khung hinh.")
            print(f"    Dang ky ket thuc voi {saved} anh.\n")
            if saved > 0:
                add_member(member_id, name, image_count=saved)
                print(f"[OK] Dang ky thanh cong: {name} ({member_id}) — {saved} anh\n")
                return True
            else:
                print("[LOI] Chua luu duoc anh nao.")
                return False

        # CHANGED: Tự động chụp nếu phát hiện đúng 1 khuôn mặt
        current_time = time.time()
        if num_faces == 1 and (current_time - last_capture_time) >= capture_interval:
            saved += 1
            fname = member_dir / f"face_{saved:04d}.jpg"
            cv2.imwrite(str(fname), frame)
            last_capture_time = current_time
            
            # Hiển thị tiến độ mỗi 10 ảnh
            if saved % 10 == 0:
                print(f"  [+] Da chup: {saved}/{num_captures} anh")

        # Hiển thị thông tin
        status_text = f"Dang ky: {name}  |  Da chup: {saved}/{num_captures}"
        if num_faces == 0:
            status_text += "  |  [Chua phat hien khuon mat]"
        elif num_faces == 1:
            status_text += "  |  [Dang chup...]"
        
        draw_header(display, status_text)
        
        cv2.putText(display,
                    "Q: Dung  |  Tu dong chup khi co 1 khuon mat",
                    (10, display.shape[0] - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_INFO, 2)
        
        cv2.imshow("Dang Ky Khuon Mat", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            print(f"\n  [!] Da dung thu cong. Luu duoc {saved} anh.")
            break

    cap.release()
    cv2.destroyAllWindows()

    if saved > 0:
        add_member(member_id, name, image_count=saved)
        print(f"\n[OK] Dang ky thanh cong: {name} ({member_id}) — {saved} anh\n")
        return True

    print("[LOI] Khong luu duoc anh nao. Huy dang ky.")
    return False


# ============================================================
# ĐĂNG KÝ TỪ FILE ẢNH
# ============================================================
def register_from_images(member_id: str, name: str,
                         image_paths: list[str] | str) -> bool:
    """
    Đăng ký khuôn mặt bằng cách copy ảnh có sẵn vào database.

    Args:
        member_id   : Mã thành viên
        name        : Họ và tên
        image_paths : Đường dẫn ảnh (str) hoặc danh sách ảnh (list)

    Returns:
        True nếu copy được ít nhất 1 ảnh.
    """
    init_directories()

    # Chuẩn hoá thành list
    if isinstance(image_paths, str):
        image_paths = [image_paths]

    member_dir = DB_PATH / member_id
    member_dir.mkdir(exist_ok=True)

    saved = 0
    for idx, path in enumerate(image_paths, 1):
        src = Path(path)
        if not src.exists():
            print(f"  [!] Khong tim thay file: {path}")
            continue
        dest = member_dir / f"face_{idx:04d}{src.suffix.lower()}"
        shutil.copy(src, dest)
        saved += 1
        print(f"  [+] Copy: {src.name} → {dest.name}")

    if saved > 0:
        # Cộng dồn nếu thành viên đã có ảnh trước đó
        from database import load_members
        existing = load_members().get(member_id, {})
        total = existing.get("image_count", 0) + saved
        add_member(member_id, name, image_count=total)
        print(f"\n[OK] Dang ky thanh cong: {name} ({member_id}) — {saved} anh\n")
        return True

    print("[LOI] Khong copy duoc anh nao.")
    return False


# ============================================================
# HÀM TỔNG HỢP (gọi từ GUI hoặc CLI)
# ============================================================
def register_member(member_id: str, name: str,
                    image_source=None,
                    num_captures: int = 200) -> bool:  # CHANGED: Mặc định 200
    """
    Đăng ký thành viên — tự chọn phương thức phù hợp.

    Args:
        member_id    : Mã định danh
        name         : Họ và tên
        image_source : None       → webcam
                       str        → 1 file ảnh
                       list[str]  → nhiều file ảnh
        num_captures : Số ảnh chụp webcam (mặc định 200)

    Returns:
        True nếu đăng ký thành công.
    """
    if image_source is None:
        return register_from_webcam(member_id, name, num_captures)
    else:
        return register_from_images(member_id, name, image_source)


# ============================================================
# CHẠY ĐỘC LẬP QUA COMMAND LINE
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("\nDung: python register.py <ID> <Ho ten> [duong_dan_anh]")
        print("\nVi du:")
        print("  python register.py SV001 'Nguyen Van A'")
        print("  python register.py SV002 'Tran Thi B' /path/anh.jpg")
        print("  python register.py --list")
        print("  python register.py --delete SV001")
        sys.exit(0)

    if sys.argv[1] == "--list":
        list_members()
    elif sys.argv[1] == "--delete" and len(sys.argv) >= 3:
        delete_member(sys.argv[2])
    else:
        mid  = sys.argv[1]
        name = sys.argv[2]
        src  = sys.argv[3] if len(sys.argv) > 3 else None
        register_member(mid, name, image_source=src)