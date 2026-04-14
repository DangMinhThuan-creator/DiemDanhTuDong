"""
main.py — Điểm vào chính
=========================
Chạy:
    python main.py        → Mở giao diện đồ hoạ trực tiếp
    
Hoặc dùng CLI (tuỳ chọn):
    python main.py register <ID> <Ten>
    python main.py attend   [ten_phien]
    ...
"""

import sys
from database import init_directories, list_members, delete_member


def main():
    init_directories()

    # Không có tham số → mở GUI luôn
    if len(sys.argv) < 2:
        from gui import AttendanceApp
        AttendanceApp().mainloop()
        return

    cmd = sys.argv[1].lower()

    if cmd == "gui":
        from gui import AttendanceApp
        AttendanceApp().mainloop()

    elif cmd == "register":
        if len(sys.argv) < 4:
            print("Dung: python main.py register <ID> <Ho ten> [anh.jpg]")
            sys.exit(1)
        from register import register_member
        mid   = sys.argv[2]
        name  = sys.argv[3]
        src   = sys.argv[4] if len(sys.argv) > 4 else None
        register_member(mid, name, image_source=src)

    elif cmd in ("attend", "attendance"):
        from attendance import run_attendance
        session  = sys.argv[2] if len(sys.argv) > 2 else None
        analysis = "--analysis" in sys.argv
        run_attendance(session_name=session, show_analysis=analysis)

    elif cmd == "report":
        from report import print_session_report
        session = sys.argv[2] if len(sys.argv) > 2 else None
        print_session_report(session)

    elif cmd == "weekly":
        from report import print_weekly_report
        print_weekly_report()

    elif cmd == "export":
        from report import export_summary_csv
        out = sys.argv[2] if len(sys.argv) > 2 else None
        export_summary_csv(out)

    elif cmd == "list":
        list_members()

    elif cmd == "delete":
        if len(sys.argv) < 3:
            print("Dung: python main.py delete <ID>")
            sys.exit(1)
        delete_member(sys.argv[2])

    else:
        print(f"[LOI] Lenh khong hop le: '{cmd}'")
        sys.exit(1)


if __name__ == "__main__":
    main()