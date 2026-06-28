"""日志查看对话框。

展示应用日志，支持级别筛选、关键字搜索、复制和清空操作。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from core.log_viewer import (
    LogEntry,
    clear_logs,
    count_logs,
    get_file_size,
    read_logs,
)


class LogDialog:
    """日志查看对话框。

    用法:
        dialog = LogDialog(parent=root)
        dialog.wait()
    """

    def __init__(self, parent: tk.Widget) -> None:
        self._parent = parent

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("日志查看")
        self._dialog.geometry("720x460")
        self._dialog.resizable(True, True)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        """构建界面。"""
        # --- 工具栏 ---
        toolbar = ttk.Frame(self._dialog, padding="5")
        toolbar.pack(fill=tk.X)

        # 级别筛选
        ttk.Label(toolbar, text="级别:").pack(side=tk.LEFT, padx=(0, 5))
        self._level_var = tk.StringVar(value="ALL")
        level_cb = ttk.Combobox(
            toolbar,
            textvariable=self._level_var,
            values=["ALL", "INFO", "WARNING", "ERROR"],
            width=10,
            state="readonly",
        )
        level_cb.pack(side=tk.LEFT, padx=(0, 15))
        level_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh())

        # 搜索
        ttk.Label(toolbar, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self._search_var = tk.StringVar()
        search_entry = ttk.Entry(
            toolbar, textvariable=self._search_var, width=30
        )
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        search_entry.bind("<KeyRelease>", lambda e: self._refresh())

        # 刷新
        ttk.Button(toolbar, text="刷新", width=8, command=self._refresh).pack(
            side=tk.LEFT, padx=2
        )

        # 复制全部
        ttk.Button(
            toolbar, text="复制", width=8, command=self._copy_all
        ).pack(side=tk.LEFT, padx=2)

        # 清空
        ttk.Button(
            toolbar, text="清空", width=8, command=self._do_clear
        ).pack(side=tk.LEFT, padx=2)

        # --- 列表区域 ---
        list_frame = ttk.Frame(self._dialog)
        list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("time", "level", "source", "message")
        self._tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=20,
        )

        self._tree.heading("time", text="时间", command=lambda: self._sort("time"))
        self._tree.heading("level", text="级别", command=lambda: self._sort("level"))
        self._tree.heading("source", text="来源", command=lambda: self._sort("source"))
        self._tree.heading("message", text="消息", command=lambda: self._sort("message"))

        self._tree.column("time", width=150, minwidth=120)
        self._tree.column("level", width=70, minwidth=60)
        self._tree.column("source", width=100, minwidth=60)
        self._tree.column("message", width=350, minwidth=150)

        vsb = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self._tree.yview
        )
        hsb = ttk.Scrollbar(
            list_frame, orient=tk.HORIZONTAL, command=self._tree.xview
        )
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # --- 底部状态栏 ---
        self._status = ttk.Frame(self._dialog, padding="5")
        self._status.pack(fill=tk.X)

        self._count_label = ttk.Label(self._status, text="")
        self._count_label.pack(side=tk.LEFT)

        self._size_label = ttk.Label(self._status, text="")
        self._size_label.pack(side=tk.LEFT, padx=20)

        ttk.Button(
            self._status, text="关闭", command=self._dialog.destroy
        ).pack(side=tk.RIGHT)

    def _refresh(self) -> None:
        """刷新列表。"""
        # 清空
        for row in self._tree.get_children():
            self._tree.delete(row)

        level = self._level_var.get()
        if level == "ALL":
            level = None

        keyword = self._search_var.get().strip() or None

        entries = read_logs(level_filter=level, keyword=keyword)
        for e in entries:
            tag = e.level.lower()
            self._tree.insert(
                "",
                tk.END,
                values=(
                    e.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    e.level,
                    e.logger_name,
                    e.message,
                ),
                tags=(tag,),
            )

        # 标签颜色
        self._tree.tag_configure("error", foreground="#c62828")
        self._tree.tag_configure("warning", foreground="#e65100")

        # 状态栏
        count = count_logs(level_filter=level, keyword=keyword)
        size = get_file_size()
        self._count_label.configure(text=f"显示 {len(entries)} / {count} 条")
        self._size_label.configure(text=f"日志大小: {size / 1024:.1f} KB")

    def _sort(self, col: str) -> None:
        """按列排序。"""
        items = [(self._tree.set(i, col), i) for i in self._tree.get_children()]
        items.sort()
        for idx, (_, i) in enumerate(items):
            self._tree.move(i, "", idx)

    def _copy_all(self) -> None:
        """复制全部日志到剪贴板。"""
        content = []
        for i in self._tree.get_children():
            values = self._tree.item(i, "values")
            content.append(" | ".join(str(v) for v in values))
        if content:
            self._dialog.clipboard_clear()
            self._dialog.clipboard_append("\n".join(content))

    def _do_clear(self) -> None:
        """清空日志文件。"""
        if messagebox.askyesno(
            "确认清空",
            "确定清空所有日志？\n此操作不可撤销。",
            parent=self._dialog,
        ):
            clear_logs()
            self._refresh()

    def wait(self) -> None:
        """等待对话框关闭。"""
        self._dialog.wait_window()