"""翻译导出对话框。

选择导出范围、格式和保存路径。
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from core.export import export_entries, get_export_entries
from core.logger import HistoryManager


class ExportDialog:
    """导出对话框。

    用法:
        dialog = ExportDialog(parent=root)
        dialog.wait()
    """

    def __init__(self, parent: tk.Widget) -> None:
        self._parent = parent
        self._manager = HistoryManager()
        self._entries = get_export_entries(self._manager)

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("导出翻译")
        self._dialog.geometry("420x300")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()

    def _build_ui) -> None:
        """构建界面。"""
        frame = ttk.Frame(self._dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)

        # 范围
        ttk.Label(frame, text="导出范围:", font=("", 10, "bold")).pack(
            anchor=tk.W, pady=(0, 5)
        )

        self._range_var = tk.StringVar(value="all")
        ttk.Radiobutton(
            frame,
            text=f"全部 ({len(self._entries)} 条)",
            variable=self._range_var,
            value="all",
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            frame,
            text="最近 50 条",
            variable=self._range_var,
            value="50",
        ).pack(anchor=tk.W, pady=2)
        ttk.Radiobutton(
            frame,
            text="最近 100 条",
            variable=self._range_var,
            value="100",
        ).pack(anchor=tk.W, pady=2)

        # 格式
        ttk.Label(frame, text="导出格式:", font=("", 10, "bold")).pack(
            anchor=tk.W, pady=(15, 5)
        )

        self._format_var = tk.StringVar(value="txt")
        fmt_frame = ttk.Frame(frame)
        fmt_frame.pack(fill=tk.X)
        ttk.Radiobutton(
            fmt_frame, text="TXT", variable=self._format_var, value="txt"
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            fmt_frame, text="CSV", variable=self._format_var, value="csv"
        ).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Radiobutton(
            fmt_frame, text="JSON", variable=self._format_var, value="json"
        ).pack(side=tk.LEFT)

        # 按钮
        btn_frame = ttk.Frame(self._dialog, padding="10")
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="导出", width=10, command=self._do_export
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            btn_frame, text="取消", width=10, command=self._dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def _do_export(self) -> None:
        """执行导出。"""
        if not self._entries:
            messagebox.showinfo("提示", "没有可导出的记录", parent=self._dialog)
            return

        # 范围
        range_val = self._range_var.get()
        if range_val == "all":
            entries = self._entries
        else:
            limit = int(range_val)
            entries = self._entries[:limit]

        # 格式
        fmt = self._format_var.get()

        # 文件路径
        ext_map = {"txt": ".txt", "csv": ".csv", "json": ".json"}
        default_name = f"translations-{datetime.now():%Y%m%d}{ext_map[fmt]}"

        file_path = filedialog.asksaveasfilename(
            parent=self._dialog,
            title="保存导出文件",
            defaultextension=ext_map[fmt],
            filetypes=[
                ("文本文件", "*.txt"),
                ("CSV 文件", "*.csv"),
                ("JSON 文件", "*.json"),
            ],
            initialfile=default_name,
        )
        if not file_path:
            return

        success = export_entries(entries, Path(file_path), fmt)
        if success:
            from ui.toast import Toast
            Toast.success(
                self._dialog, f"已导出 {len(entries)} 条到:\n{file_path}"
            )
            self._dialog.destroy()
        else:
            messagebox.showerror(
                "导出失败", "无法写入文件，请检查路径权限。", parent=self._dialog
            )

    def wait(self) -> None:
        """等待对话框关闭。"""
        self._dialog.wait_window()