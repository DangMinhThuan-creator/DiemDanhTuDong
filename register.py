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
# ĐĂNG KÝ TỪ WEBCAM
# ============================================================
def register_from_webcam(member_id: str, name: str,
                         num_captures: int = DEFAULT_CAPTURE_COUNT) -> bool:
    """
    Mở webcam và chụp nhiều ảnh khuôn mặt để đăng ký.

    Hướng dẫn khi chụp:
      - Nhìn thẳng vào camera
      - Xoay đầu nhẹ sang trái/phải/trên/dưới giữa các lần chụp
      - Nhấn SPACE khi khuôn mặt nằm trong khung xanh
      - Nhấn Q để huỷ

    Args:
        member_id   : Mã thành viên (VD: "SV001")
        name        : Họ và tên
        num_captures: Số ảnh cần chụp

    Returns:
        True nếu đăng ký thành công (lưu được ít nhất 1 ảnh).
    """
    init_directories()

    member_dir = DB_PATH / member_id
    member_dir.mkdir(exist_ok=True)

    print(f"\n[*] Dang ky khuon mat: {name}  (ID: {member_id})")
    print(f"    Can chup {num_captures} anh — hay nhin vao camera.")
    print("    SPACE: chup anh  |  Q: huy\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[LOI] Khong mo duoc webcam.")
        return False

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    saved = 0

    while saved < num_captures:
        ret, frame = cap.read()
        if not ret:
            break

        display = frame.copy()
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces   = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))

        for (x, y, w, h) in faces:
            cv2.rectangle(display, (x, y), (x + w, y + h), COLOR_SUCCESS, 2)

        draw_header(display,
                    f"Dang ky: {name}  |  Da chup: {saved}/{num_captures}")
        cv2.putText(display,
                    "SPACE: Chup  |  Q: Huy",
                    (10, display.shape[0] - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_INFO, 2)
        cv2.imshow("Dang Ky Khuon Mat", display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            if len(faces) == 0:
                print("  [!] Chua phat hien khuon mat — hay dieu chinh vi tri.")
                continue
            saved += 1
            fname = member_dir / f"face_{saved:04d}.jpg"
            cv2.imwrite(str(fname), frame)
            print(f"  [+] Luu anh {saved}/{num_captures}: {fname.name}")
        elif key == ord("q"):
            print("  [!] Da huy dang ky.")
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
                    num_captures: int = DEFAULT_CAPTURE_COUNT) -> bool:
    """
    Đăng ký thành viên — tự chọn phương thức phù hợp.

    Args:
        member_id    : Mã định danh
        name         : Họ và tên
        image_source : None       → webcam
                       str        → 1 file ảnh
                       list[str]  → nhiều file ảnh
        num_captures : Số ảnh chụp webcam (chỉ dùng khi image_source=None)

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
