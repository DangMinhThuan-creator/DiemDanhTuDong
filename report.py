"""
report.py — Báo cáo & thống kê điểm danh
==========================================
Các loại báo cáo:
  - Báo cáo 1 phiên: ai có mặt / vắng mặt, giờ điểm danh
  - Tổng hợp nhiều phiên: bảng ma trận ✓/✗ theo người × phiên
  - Xuất CSV tổng hợp

Chạy độc lập:
    python report.py                  → báo cáo hôm nay
    python report.py ToanA1_Buoi3     → báo cáo phiên cụ thể
    python report.py --weekly         → tổng hợp tất cả phiên
    python report.py --export         → xuất CSV tổng hợp
"""

import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from config import ATTENDANCE_PATH
from database import load_members


# ============================================================
# BÁO CÁO 1 PHIÊN
# ============================================================
def get_session_data(session_name: str) -> tuple[dict, dict]:
    """
    Đọc dữ liệu 1 phiên điểm danh.

    Returns:
        (attended, members)
        attended = {member_id: time_str}
        members  = {member_id: info_dict}
    """
    csv_file = ATTENDANCE_PATH / f"{session_name}.csv"
    members  = load_members()
    attended = {}

    if csv_file.exists():
        with open(csv_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                attended[row["member_id"]] = row.get("time") or row.get("Time") or row.get("time_str") or "N/A"

    return attended, members


def print_session_report(session_name: str = None):
    """
    In báo cáo điểm danh 1 phiên ra console.

    Args:
        session_name: Tên phiên. Mặc định = ngày hôm nay.
    """
    if not session_name:
        session_name = date.today().strftime("%Y-%m-%d")

    csv_file = ATTENDANCE_PATH / f"{session_name}.csv"
    if not csv_file.exists():
        print(f"[!] Khong tim thay file: {csv_file.name}")
        print(f"    Cac phien co san: {list_sessions()}")
        return

    attended, members = get_session_data(session_name)
    absent = [mid for mid in members if mid not in attended]

    W = 60
    print(f"\n{'='*W}")
    print(f"  BAO CAO DIEM DANH — Phien: {session_name}")
    print(f"{'='*W}")
    print(f"  Co mat  : {len(attended)}/{len(members)} nguoi")
    print(f"  Vang mat: {len(absent)}/{len(members)} nguoi")

    if attended:
        print(f"\n  ✓ CO MAT ({len(attended)} nguoi)")
        print(f"  {'ID':<14} {'Ho va ten':<26} Gio diem danh")
        print(f"  {'-'*52}")
        for mid, t in sorted(attended.items(), key=lambda x: x[1]):
            name = members.get(mid, {}).get("name", mid)
            print(f"  {mid:<14} {name:<26} {t}")

    if absent:
        print(f"\n  ✗ VANG MAT ({len(absent)} nguoi)")
        print(f"  {'ID':<14} Ho va ten")
        print(f"  {'-'*40}")
        for mid in sorted(absent):
            name = members.get(mid, {}).get("name", mid)
            print(f"  {mid:<14} {name}")

    print(f"{'='*W}\n")


# ============================================================
# BÁO CÁO TỔNG HỢP NHIỀU PHIÊN
# ============================================================
def get_all_sessions() -> list[str]:
    """Lấy danh sách tất cả phiên có file CSV, sắp xếp theo thời gian."""
    if not ATTENDANCE_PATH.exists():
        return []
    return sorted([f.stem for f in ATTENDANCE_PATH.glob("*.csv")])


def list_sessions() -> list[str]:
    """Trả về và in danh sách phiên."""
    sessions = get_all_sessions()
    if sessions:
        print(f"\n  Cac phien hien co ({len(sessions)} phien):")
        for s in sessions:
            print(f"    - {s}")
    else:
        print("  [!] Chua co phien nao.")
    return sessions


def print_weekly_report(sessions: list[str] = None):
    """
    In bảng tổng hợp điểm danh tất cả phiên.
    Dạng ma trận: hàng = người, cột = phiên.

    Args:
        sessions: Danh sách phiên cần tổng hợp.
                  Mặc định = tất cả phiên tìm được.
    """
    if sessions is None:
        sessions = get_all_sessions()

    if not sessions:
        print("[!] Chua co du lieu diem danh.")
        return

    members = load_members()
    if not members:
        print("[!] Chua co thanh vien nao.")
        return

    # Xây dựng ma trận stats[member_id][session] = 1/0
    stats = defaultdict(lambda: defaultdict(int))
    for session in sessions:
        csv_file = ATTENDANCE_PATH / f"{session}.csv"
        if not csv_file.exists():
            continue
        with open(csv_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                stats[row["member_id"]][session] = 1

    # Rút gọn tên phiên để vừa cột (lấy 8 ký tự cuối)
    short = {s: s[-8:] for s in sessions}

    W = max(60, 24 + 9 * len(sessions))
    print(f"\n{'='*W}")
    print(f"  TONG HOP DIEM DANH  —  {len(sessions)} phien  |  {len(members)} thanh vien")
    print(f"{'='*W}")

    # Header
    header = f"  {'Ho va ten':<22}"
    for s in sessions:
        header += f" {short[s]:>8}"
    header += "   Tong"
    print(header)
    print(f"  {'-'*(W-2)}")

    # Từng thành viên
    for mid, info in sorted(members.items()):
        name  = info["name"]
        total = sum(stats[mid][s] for s in sessions)
        row   = f"  {name:<22}"
        for s in sessions:
            mark = " ✓" if stats[mid][s] else " ✗"
            row += f" {mark:>8}"
        row += f"   {total}/{len(sessions)}"
        print(row)

    print(f"{'='*W}\n")


# ============================================================
# XUẤT CSV TỔNG HỢP
# ============================================================
def export_summary_csv(output_path: str = None) -> Path:
    """
    Xuất bảng tổng hợp tất cả phiên ra file CSV.

    Args:
        output_path: Đường dẫn file output. Mặc định = attendance_records/summary.csv

    Returns:
        Path file CSV đã tạo.
    """
    sessions = get_all_sessions()
    members  = load_members()

    if not sessions or not members:
        print("[!] Khong co du lieu de xuat.")
        return None

    stats = defaultdict(lambda: defaultdict(int))
    for session in sessions:
        csv_file = ATTENDANCE_PATH / f"{session}.csv"
        if not csv_file.exists():
            continue
        with open(csv_file, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                stats[row["member_id"]][session] = 1

    out = Path(output_path) if output_path else ATTENDANCE_PATH / "summary.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig cho Excel
        writer = csv.writer(f)
        writer.writerow(["ID", "Ho va ten"] + sessions + ["Tong co mat", "Ti le (%)"])
        for mid, info in sorted(members.items()):
            total = sum(stats[mid][s] for s in sessions)
            rate  = round(total / len(sessions) * 100, 1) if sessions else 0
            row   = [mid, info["name"]]
            row  += [1 if stats[mid][s] else 0 for s in sessions]
            row  += [total, f"{rate}%"]
            writer.writerow(row)

    print(f"[OK] Da xuat bao cao: {out}")
    return out


# ============================================================
# CHẠY ĐỘC LẬP
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--today":
        print_session_report()
    elif sys.argv[1] == "--weekly":
        print_weekly_report()
    elif sys.argv[1] == "--list":
        list_sessions()
    elif sys.argv[1] == "--export":
        export_summary_csv()
    else:
        print_session_report(sys.argv[1])
