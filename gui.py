"""
gui.py — Giao diện đồ họa chính (Tkinter)
==========================================
Cửa sổ chính với sidebar điều hướng 4 tab:
  - Điểm Danh  : bắt đầu/dừng phiên, nhật ký real-time
  - Đăng Ký    : thêm thành viên qua webcam hoặc ảnh
  - Báo Cáo    : bảng có mặt/vắng mặt theo phiên
  - Danh Sách  : quản lý danh sách thành viên

Chạy:
    python gui.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import csv
import io
import sys
from datetime import date
from pathlib import Path

from config import (
    ATTENDANCE_PATH,
    BG_DARK, BG_CARD, BG_PANEL,
    ACCENT, SUCCESS, WARNING, DANGER,
    TEXT_MAIN, TEXT_MUTE,
    FONT_HEAD, FONT_BODY, FONT_MONO,
)
from database import init_directories, load_members
from register import register_member
from database import delete_member
from attendance import run_attendance
from report import (
    print_session_report, print_weekly_report,
    export_summary_csv, get_all_sessions,
    get_session_data,
)


# ============================================================
# WIDGET DÙNG CHUNG
# ============================================================
class RoundedButton(tk.Canvas):
    """Nút bấm bo góc với hiệu ứng hover."""

    def __init__(self, parent, text, command=None, color=ACCENT,
                 width=160, height=38, radius=10, **kw):

        self._cmd        = command
        self._color      = color
        self._hover      = _lighten(color)
        self._text       = text
        self._btn_width  = int(width)    # tên khác để tránh bị Canvas ghi đè
        self._btn_height = int(height)
        self._btn_radius = int(radius)

        super().__init__(parent, width=int(width), height=int(height),
                         bg=parent["bg"], highlightthickness=0, **kw)

        self._draw(color)
        self.bind("<Enter>",    lambda e: self._draw(self._hover))
        self.bind("<Leave>",    lambda e: self._draw(color))
        self.bind("<Button-1>", lambda e: command() if command else None)

    def _draw(self, color):
        self.delete("all")
        r = self._btn_radius
        w = self._btn_width
        h = self._btn_height
        for sx, sy, start in [(0, 0, 90), (w-2*r, 0, 0), (0, h-2*r, 180), (w-2*r, h-2*r, 270)]:
            self.create_arc(sx, sy, sx+2*r, sy+2*r,
                            start=start, extent=90, fill=color, outline=color)
        self.create_rectangle(r, 0, w-r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h-r, fill=color, outline=color)
        self.create_text(w//2, h//2, text=self._text,
                         fill="white", font=("Segoe UI", 10, "bold"))


def _lighten(hex_color: str) -> str:
    r = min(255, int(hex_color[1:3], 16) + 28)
    g = min(255, int(hex_color[3:5], 16) + 28)
    b = min(255, int(hex_color[5:7], 16) + 28)
    return f"#{r:02x}{g:02x}{b:02x}"


def lbl(parent, text, font=FONT_BODY, fg=TEXT_MAIN, bg=BG_CARD, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)


def entry(parent, width=24, var=None, **kw):
    kw_entry = dict(width=width, font=FONT_BODY,
                    bg=BG_PANEL, fg=TEXT_MAIN,
                    insertbackground=TEXT_MAIN,
                    relief="flat", bd=6)
    kw_entry.update(kw)
    if var:
        kw_entry["textvariable"] = var
    return tk.Entry(parent, **kw_entry)


def separator(parent):
    return tk.Frame(parent, bg=BG_PANEL, height=1)


# ============================================================
# ỨNG DỤNG CHÍNH
# ============================================================
class AttendanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        init_directories()
        self.title("Hệ Thống Điểm Danh — OpenCV + DeepFace")
        self.configure(bg=BG_DARK)
        self.geometry("1120x740")
        self.resizable(True, True)
        self._build_layout()

    # ----------------------------------------------------------
    # LAYOUT CHÍNH
    # ----------------------------------------------------------
    def _build_layout(self):
        # Sidebar
        self._sidebar = tk.Frame(self, bg=BG_CARD, width=230)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)
        self._build_sidebar()

        # Vùng nội dung
        content = tk.Frame(self, bg=BG_DARK)
        content.pack(side="left", fill="both", expand=True)

        self._tabs = {}
        self._tab_builders = {
            "attendance": self._build_tab_attendance,
            "register":   self._build_tab_register,
            "report":     self._build_tab_report,
            "members":    self._build_tab_members,
        }
        for key in self._tab_builders:
            frame = tk.Frame(content, bg=BG_DARK)
            self._tabs[key] = frame
            self._tab_builders[key](frame)

        self._switch_tab("attendance")

    def _build_sidebar(self):
        sb = self._sidebar
        tk.Label(sb, text="🎓 Điểm Danh AI",
                 font=("Segoe UI", 15, "bold"),
                 fg=ACCENT, bg=BG_CARD).pack(pady=(30, 4))
        tk.Label(sb, text="OpenCV + DeepFace",
                 font=("Segoe UI", 9), fg=TEXT_MUTE, bg=BG_CARD).pack()

        separator(sb).pack(fill="x", padx=16, pady=18)

        nav = [
            ("📋  Điểm Danh",  "attendance"),
            ("👤  Đăng Ký",    "register"),
            ("📊  Báo Cáo",    "report"),
            ("👥  Danh Sách",  "members"),
        ]
        self._nav_btns = {}
        for text, key in nav:
            b = tk.Button(sb, text=text, font=("Segoe UI", 11),
                          fg=TEXT_MAIN, bg=BG_CARD, bd=0,
                          cursor="hand2", anchor="w", padx=22,
                          activebackground=BG_PANEL, activeforeground=ACCENT,
                          command=lambda k=key: self._switch_tab(k))
            b.pack(fill="x", ipady=11)
            self._nav_btns[key] = b

        separator(sb).pack(fill="x", padx=16, pady=18)
        self._status_lbl = tk.Label(sb, text="● Sẵn sàng",
                                    font=("Segoe UI", 9),
                                    fg=SUCCESS, bg=BG_CARD, anchor="w")
        self._status_lbl.pack(fill="x", padx=18)

    def _switch_tab(self, key: str):
        for k, f in self._tabs.items():
            f.pack_forget()
        self._tabs[key].pack(fill="both", expand=True)
        for k, b in self._nav_btns.items():
            b.configure(bg=BG_PANEL if k == key else BG_CARD,
                        fg=ACCENT   if k == key else TEXT_MAIN)

    def _set_status(self, text: str, color: str = SUCCESS):
        self._status_lbl.configure(text=f"● {text}", fg=color)

    # ----------------------------------------------------------
    # TAB: ĐIỂM DANH
    # ----------------------------------------------------------
    def _build_tab_attendance(self, tab: tk.Frame):
        lbl(tab, "Điểm Danh Tự Động", font=FONT_HEAD, bg=BG_DARK
            ).pack(anchor="w", padx=30, pady=(28, 6))

        # Card cấu hình phiên
        card = tk.Frame(tab, bg=BG_CARD)
        card.pack(fill="x", padx=30, pady=8)
        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="x", padx=20, pady=16)

        lbl(inner, "Tên phiên:", bg=BG_CARD).pack(side="left")
        self._session_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        entry(inner, width=28, var=self._session_var).pack(side="left", padx=(10, 20))

        self._analysis_var = tk.BooleanVar(value=False)
        tk.Checkbutton(inner, text="Phân tích cảm xúc / tuổi / giới tính",
                       variable=self._analysis_var,
                       bg=BG_CARD, fg=TEXT_MUTE, selectcolor=BG_PANEL,
                       activebackground=BG_CARD, font=FONT_BODY
                       ).pack(side="left")

        # Nút bắt đầu
        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.pack(pady=(4, 18))
        RoundedButton(btn_row, "▶  Bắt Đầu Điểm Danh",
                      command=self._start_attendance,
                      color=SUCCESS, width=210).pack(side="left", padx=8)
        RoundedButton(btn_row, "📊  Xem Báo Cáo",
                      command=lambda: self._switch_tab("report"),
                      color=ACCENT, width=160).pack(side="left", padx=8)

        # Nhật ký
        log_frame = tk.Frame(tab, bg=BG_CARD)
        log_frame.pack(fill="both", expand=True, padx=30, pady=(0, 26))
        lbl(log_frame, "Nhật ký điểm danh",
            font=("Segoe UI", 10, "bold"), bg=BG_CARD
            ).pack(anchor="w", padx=16, pady=(12, 4))
        self._log = tk.Text(log_frame, font=FONT_MONO, bg=BG_PANEL,
                            fg=TEXT_MAIN, relief="flat", bd=0,
                            state="disabled")
        self._log.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self._log.tag_config("ok",   foreground=SUCCESS)
        self._log.tag_config("warn", foreground="#f6c843")
        self._log.tag_config("info", foreground=ACCENT)

    def _log_write(self, msg: str, tag: str = "info"):
        self._log.configure(state="normal")
        self._log.insert("end", msg + "\n", tag)
        self._log.see("end")
        self._log.configure(state="disabled")

    def _start_attendance(self):
        session  = self._session_var.get().strip() or date.today().strftime("%Y-%m-%d")
        analysis = self._analysis_var.get()
        members  = load_members()

        if not members:
            messagebox.showerror("Lỗi", "Chưa có thành viên. Hãy đăng ký trước.")
            return

        self._log_write(f"\n▶ Bắt đầu phiên: {session}", "info")
        self._set_status("Đang điểm danh...", WARNING)

        def _on_checkin(mid, name, t):
            self.after(0, lambda: self._log_write(
                f"  ✓  {name:<24} {mid:<12}  {t}", "ok"))

        def _worker():
            run_attendance(session_name=session,
                           show_analysis=analysis,
                           on_checkin=_on_checkin)
            self.after(0, self._on_attendance_done, session)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_attendance_done(self, session: str):
        self._set_status("Sẵn sàng", SUCCESS)
        csv_file = ATTENDANCE_PATH / f"{session}.csv"
        count = 0
        if csv_file.exists():
            with open(csv_file, "r", encoding="utf-8") as f:
                count = sum(1 for _ in csv.reader(f)) - 1
        self._log_write(
            f"\n■ Kết thúc phiên '{session}' — {count} người đã điểm danh\n", "info")

    # ----------------------------------------------------------
    # TAB: ĐĂNG KÝ
    # ----------------------------------------------------------
    def _build_tab_register(self, tab: tk.Frame):
        lbl(tab, "Đăng Ký Thành Viên", font=FONT_HEAD, bg=BG_DARK
            ).pack(anchor="w", padx=30, pady=(28, 6))

        card = tk.Frame(tab, bg=BG_CARD)
        card.pack(fill="x", padx=30, pady=8)
        form = tk.Frame(card, bg=BG_CARD)
        form.pack(padx=24, pady=20)

        self._reg = {}
        fields = [("Mã thành viên (ID):", "id"), ("Họ và tên:", "name")]
        for i, (txt, key) in enumerate(fields):
            lbl(form, txt, bg=BG_CARD).grid(row=i, column=0,
                                            sticky="w", pady=10, padx=(0, 16))
            var = tk.StringVar()
            self._reg[key] = var
            entry(form, width=32, var=var).grid(row=i, column=1, sticky="w", pady=10)

        btn_row = tk.Frame(card, bg=BG_CARD)
        btn_row.pack(pady=(4, 20))
        RoundedButton(btn_row, "📷  Đăng ký qua Webcam",
                      command=self._reg_webcam,
                      color=ACCENT, width=200).pack(side="left", padx=8)
        RoundedButton(btn_row, "🗂  Chọn File Ảnh",
                      command=self._reg_file,
                      color="#7c5cbf", width=160).pack(side="left", padx=8)
        RoundedButton(btn_row, "🗑  Xoá Thành Viên",
                      command=self._del_member,
                      color=DANGER, width=160).pack(side="left", padx=8)

        lbl(tab,
            "Tip: Chụp ít nhất 5 ảnh từ nhiều góc (thẳng, trái, phải, nghiêng) để tăng độ chính xác.",
            font=("Segoe UI", 9), fg=TEXT_MUTE, bg=BG_DARK
            ).pack(anchor="w", padx=30)

    def _reg_info(self):
        mid  = self._reg["id"].get().strip()
        name = self._reg["name"].get().strip()
        if not mid or not name:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập ID và họ tên.")
            return None, None
        return mid, name

    def _reg_webcam(self):
        mid, name = self._reg_info()
        if not mid:
            return
        def _w():
            ok = register_member(mid, name)
            self.after(0, self._refresh_members_tab)
            msg = f"Đã đăng ký: {name}" if ok else "Đăng ký thất bại."
            self.after(0, lambda: messagebox.showinfo("Kết quả", msg))
        threading.Thread(target=_w, daemon=True).start()

    def _reg_file(self):
        mid, name = self._reg_info()
        if not mid:
            return
        paths = filedialog.askopenfilenames(
            title="Chọn ảnh khuôn mặt",
            filetypes=[("Ảnh", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if not paths:
            return
        def _w():
            ok = register_member(mid, name, image_source=list(paths))
            self.after(0, self._refresh_members_tab)
            msg = f"Đã đăng ký: {name} ({len(paths)} ảnh)" if ok else "Đăng ký thất bại."
            self.after(0, lambda: messagebox.showinfo("Kết quả", msg))
        threading.Thread(target=_w, daemon=True).start()

    def _del_member(self):
        mid, _ = self._reg_info()
        if not mid:
            return
        if messagebox.askyesno("Xác nhận", f"Xoá thành viên '{mid}'?"):
            delete_member(mid)
            self._refresh_members_tab()
            messagebox.showinfo("OK", f"Đã xoá thành viên: {mid}")

    # ----------------------------------------------------------
    # TAB: BÁO CÁO
    # ----------------------------------------------------------
    def _build_tab_report(self, tab: tk.Frame):
        lbl(tab, "Báo Cáo Điểm Danh", font=FONT_HEAD, bg=BG_DARK
            ).pack(anchor="w", padx=30, pady=(28, 6))

        # Thanh điều khiển
        ctrl = tk.Frame(tab, bg=BG_DARK)
        ctrl.pack(fill="x", padx=30, pady=8)
        lbl(ctrl, "Phiên:", bg=BG_DARK).pack(side="left")
        self._rpt_session = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self._session_combo = ttk.Combobox(
            ctrl, textvariable=self._rpt_session,
            values=get_all_sessions(), width=26, font=FONT_BODY)
        self._session_combo.pack(side="left", padx=(8, 16))
        RoundedButton(ctrl, "🔄  Tải",
                      command=self._load_report,
                      color=ACCENT, width=100).pack(side="left", padx=4)
        RoundedButton(ctrl, "📅  Tổng hợp",
                      command=self._show_weekly,
                      color="#4a8a5a", width=130).pack(side="left", padx=4)
        RoundedButton(ctrl, "💾  Xuất CSV",
                      command=self._export_csv,
                      color="#7c5cbf", width=120).pack(side="left", padx=4)

        # Bảng kết quả
        frame = tk.Frame(tab, bg=BG_CARD)
        frame.pack(fill="both", expand=True, padx=30, pady=(8, 26))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Rpt.Treeview",
                        background=BG_PANEL, foreground=TEXT_MAIN,
                        fieldbackground=BG_PANEL, rowheight=28, font=FONT_BODY)
        style.configure("Rpt.Treeview.Heading",
                        background=BG_CARD, foreground=ACCENT,
                        font=("Segoe UI", 10, "bold"))
        style.map("Rpt.Treeview", background=[("selected", ACCENT)])

        cols = ("ID", "Họ tên", "Giờ điểm danh", "Trạng thái")
        self._rpt_tree = ttk.Treeview(frame, columns=cols,
                                      show="headings", style="Rpt.Treeview")
        widths = [120, 220, 140, 130]
        for col, w in zip(cols, widths):
            self._rpt_tree.heading(col, text=col)
            self._rpt_tree.column(col, width=w, anchor="center")
        self._rpt_tree.pack(fill="both", expand=True, side="left")

        sb = ttk.Scrollbar(frame, orient="vertical",
                           command=self._rpt_tree.yview)
        sb.pack(side="right", fill="y")
        self._rpt_tree.configure(yscrollcommand=sb.set)

    def _load_report(self):
        session = self._rpt_session.get().strip()
        attended, members = get_session_data(session)

        for item in self._rpt_tree.get_children():
            self._rpt_tree.delete(item)

        for mid, info in sorted(members.items()):
            if mid in attended:
                self._rpt_tree.insert("", "end",
                    values=(mid, info["name"], attended[mid], "✓ Có mặt"),
                    tags=("ok",))
            else:
                self._rpt_tree.insert("", "end",
                    values=(mid, info["name"], "—", "✗ Vắng mặt"),
                    tags=("absent",))

        self._rpt_tree.tag_configure("ok",     foreground=SUCCESS)
        self._rpt_tree.tag_configure("absent", foreground=DANGER)

    def _show_weekly(self):
        win = tk.Toplevel(self, bg=BG_DARK)
        win.title("Tổng Hợp Điểm Danh")
        win.geometry("860x500")
        txt = tk.Text(win, font=FONT_MONO, bg=BG_PANEL,
                      fg=TEXT_MAIN, relief="flat", bd=12)
        txt.pack(fill="both", expand=True)

        buf = io.StringIO()
        sys.stdout, old = buf, sys.stdout
        print_weekly_report()
        sys.stdout = old
        txt.insert("end", buf.getvalue())
        txt.configure(state="disabled")

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="summary.csv")
        if path:
            out = export_summary_csv(path)
            messagebox.showinfo("OK", f"Đã xuất: {out}")

    def _refresh_report_sessions(self):
        self._session_combo["values"] = get_all_sessions()

    # ----------------------------------------------------------
    # TAB: DANH SÁCH
    # ----------------------------------------------------------
    def _build_tab_members(self, tab: tk.Frame):
        lbl(tab, "Danh Sách Thành Viên", font=FONT_HEAD, bg=BG_DARK
            ).pack(anchor="w", padx=30, pady=(28, 6))

        frame = tk.Frame(tab, bg=BG_CARD)
        frame.pack(fill="both", expand=True, padx=30, pady=8)

        style = ttk.Style()
        style.configure("Mem.Treeview",
                        background=BG_PANEL, foreground=TEXT_MAIN,
                        fieldbackground=BG_PANEL, rowheight=30, font=FONT_BODY)
        style.configure("Mem.Treeview.Heading",
                        background=BG_CARD, foreground=ACCENT,
                        font=("Segoe UI", 10, "bold"))

        cols = ("ID", "Họ và tên", "Số ảnh", "Ngày đăng ký")
        self._mem_tree = ttk.Treeview(frame, columns=cols,
                                      show="headings", style="Mem.Treeview")
        widths = [130, 240, 100, 160]
        for col, w in zip(cols, widths):
            self._mem_tree.heading(col, text=col)
            self._mem_tree.column(col, width=w, anchor="center")
        self._mem_tree.pack(fill="both", expand=True, side="left")

        sb = ttk.Scrollbar(frame, orient="vertical",
                           command=self._mem_tree.yview)
        sb.pack(side="right", fill="y")
        self._mem_tree.configure(yscrollcommand=sb.set)

        RoundedButton(tab, "🔄  Làm mới danh sách",
                      command=self._refresh_members_tab,
                      color=ACCENT, width=200).pack(pady=14)

        self._refresh_members_tab()

    def _refresh_members_tab(self):
        if not hasattr(self, "_mem_tree"):
            return
        for item in self._mem_tree.get_children():
            self._mem_tree.delete(item)
        for mid, info in sorted(load_members().items()):
            reg = info.get("registered_at", "")[:10]
            self._mem_tree.insert("", "end",
                values=(mid, info["name"], info.get("image_count", "?"), reg))


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    app = AttendanceApp()
    app.mainloop()
