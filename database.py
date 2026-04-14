"""
database.py — Quản lý thành viên (CRUD)
========================================
Xử lý toàn bộ việc đọc/ghi thông tin thành viên
vào file members.json và tạo thư mục dữ liệu.

Các hàm:
    init_directories()          — Khởi tạo thư mục lần đầu
    load_members()              — Đọc danh sách thành viên
    save_members(members)       — Ghi danh sách thành viên
    get_member(member_id)       — Lấy thông tin 1 thành viên
    add_member(id, name, count) — Thêm thành viên mới
    delete_member(member_id)    — Xoá thành viên
    list_members()              — In danh sách ra console
"""

import json
import shutil
from datetime import datetime
from config import DB_PATH, ATTENDANCE_PATH, MEMBERS_FILE


# ============================================================
# KHỞI TẠO HỆ THỐNG
# ============================================================
def init_directories():
    """Tạo các thư mục cần thiết nếu chưa tồn tại."""
    DB_PATH.mkdir(parents=True, exist_ok=True)
    ATTENDANCE_PATH.mkdir(parents=True, exist_ok=True)
    if not MEMBERS_FILE.exists():
        MEMBERS_FILE.write_text(
            json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    print("[OK] Thu muc da san sang.")


# ============================================================
# ĐỌC / GHI THÀNH VIÊN
# ============================================================
def load_members() -> dict:
    """
    Đọc toàn bộ thành viên từ members.json.

    Returns:
        dict: {member_id: {"name": ..., "registered_at": ..., "image_count": ...}}
    """
    if MEMBERS_FILE.exists():
        try:
            return json.loads(MEMBERS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("[!] members.json bi hong, reset ve rong.")
            return {}
    return {}


def save_members(members: dict):
    """Ghi toàn bộ thành viên vào members.json."""
    MEMBERS_FILE.write_text(
        json.dumps(members, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_member(member_id: str) -> dict | None:
    """
    Lấy thông tin 1 thành viên theo ID.

    Returns:
        dict nếu tìm thấy, None nếu không có.
    """
    return load_members().get(member_id)


def add_member(member_id: str, name: str, image_count: int = 0) -> bool:
    """
    Thêm hoặc cập nhật thông tin thành viên.

    Args:
        member_id   : Mã định danh duy nhất (VD: "SV001")
        name        : Họ và tên đầy đủ
        image_count : Số ảnh đã lưu vào face_database

    Returns:
        True nếu thành công.
    """
    members = load_members()
    members[member_id] = {
        "name": name,
        "registered_at": datetime.now().isoformat(),
        "image_count": image_count,
    }
    save_members(members)
    return True


def update_member_image_count(member_id: str, count: int):
    """Cập nhật số ảnh của thành viên đã có."""
    members = load_members()
    if member_id in members:
        members[member_id]["image_count"] = count
        save_members(members)


def delete_member(member_id: str) -> bool:
    """
    Xoá thành viên: xoá thư mục ảnh lẫn record trong JSON.

    Returns:
        True nếu xoá thành công, False nếu không tìm thấy.
    """
    members = load_members()
    member_dir = DB_PATH / member_id

    found = False
    if member_dir.exists():
        shutil.rmtree(member_dir)
        found = True
    if member_id in members:
        del members[member_id]
        save_members(members)
        found = True

    if found:
        print(f"[OK] Da xoa thanh vien: {member_id}")
    else:
        print(f"[!] Khong tim thay thanh vien: {member_id}")
    return found


# ============================================================
# TIỆN ÍCH HIỂN THỊ
# ============================================================
def list_members():
    """In danh sách thành viên ra console theo dạng bảng."""
    members = load_members()
    if not members:
        print("[!] Chua co thanh vien nao duoc dang ky.")
        return

    print(f"\n{'='*60}")
    print(f"  DANH SACH THANH VIEN  —  Tong: {len(members)} nguoi")
    print(f"{'='*60}")
    print(f"  {'ID':<14} {'Ho va ten':<28} {'So anh':<8} {'Ngay DK'}")
    print(f"  {'-'*56}")
    for mid, info in members.items():
        reg = info.get("registered_at", "")[:10]
        print(f"  {mid:<14} {info['name']:<28} {info.get('image_count', '?'):<8} {reg}")
    print(f"{'='*60}\n")
