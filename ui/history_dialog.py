"""翻译历史浏览对话框。

展示历史翻译记录，支持列表查看、关键字搜索和清空操作。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from core.logger import HistoryManager


class HistoryDialog:
    """翻译历史浏览对话框。

    用法:
        dialog = HistoryDialog(parent=root)
        dialog.wait()
    """

    def __init__(self, parent: tk.Widget) -> None:
        self._manager = HistoryManager()

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("翻译历史")
        self._dialog.geometry("680x450")
        self._dialog.resizable(True, True)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """构建对话框界面。"""
        # 搜索栏
        search_frame = ttk.Frame(self._dialog, padding="5")
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))

        self._search_var = tk.StringVar()
        self._search_entry = ttk.Entry(
            search_frame, textvariable=self._search_var, width=40
        )
        self._search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self._search_entry.bind("<KeyRelease>", lambda e: self._refresh())

        ttk.Button(
            search_frame, text="清空历史", command=self._do_clear
        ).pack(side=tk.RIGHT, padx=2)

        ttk.Button(
            search_frame, text="刷新", command=self._refresh
        ).pack(side=tk.RIGHT, padx=2)

        # 列表区域
        list_frame = ttk.Frame(self._dialog, padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview 表格
        columns = ("time", "model", "source_lang", "source", "target")
        self._tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            height=15,
        )

        self._tree.heading("time", text="时间")
        self._tree.heading("model", text="模型")
        self._tree.heading("source_lang", text="语言方向")
        self._tree.heading("source", text="原文")
        self._tree.heading("target", text="译文")

        self._tree.column("time", width=150, minwidth=120)
        self._tree.column("model", width=120, minwidth=80)
        self._tree.column("source_lang", width=80, minwidth=60)
        self._tree.column("source", width=200, minwidth=120)
        self._tree.column("target", width=200, minwidth=120)

        # 滚动条
        vsb = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self._tree.yview
        )
        hsb = ttk.Scrollbar(
            list_frame, orient=tk.HORIZONTAL, command=self._tree.xview
        )
        self._tree.configure(
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set,
        )

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # 双击查看详情
        self._tree.bind("<Double-Button-1>", self._show_detail)

        # 底部统计
        self._status_frame = ttk.Frame(self._dialog, padding="5")
        self._status_frame.pack(fill=tk.X)

        self._count_label = ttk.Label(self._status_frame, text="共 0 条记录")
        self._count_label.pack(side=tk.LEFT)

        ttk.Button(
            self._status_frame, text="关闭", width=8, command=self._dialog.destroy
        ).pack(side=tk.RIGHT, padx=2)

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """根据搜索关键字刷新列表。"""
        # 清空
        for row in self._tree.get_children():
            self._tree.delete(row)

        keyword = self._search_var.get().strip()
        if keyword:
            entries = self._manager.search(keyword)
        else:
            entries = self._manager.list_entries(limit=200)

        for entry in entries:
            # 截断过长文本以保持可读性
            source_short = entry.source_text[:80].replace("\n", " ")
            target_short = entry.target_text[:80].replace("\n", " ")
            self._tree.insert(
                "",
                tk.END,
                values=(
                    entry.timestamp[:19],  # 取到秒
                    entry.model,
                    f"{entry.source_lang}→{entry.target_lang}",
                    source_short,
                    target_short,
                ),
            )

        total = self._manager.count()
        shown = len(entries)
        self._count_label.configure(
            text=f"共 {total} 条记录" + (f" (显示 {shown})" if shown < total else "")
        )

    def _do_clear(self) -> None:
        """清空所有历史记录。"""
        if not self._manager.count():
            messagebox.showinfo("提示", "历史记录已为空", parent=self._dialog)
            return
        if messagebox.askyesno(
            "确认清空", "确定清空所有翻译历史记录吗？\n此操作不可撤销。", parent=self._dialog
        ):
            self._manager.clear()
            self._refresh()
            messagebox.showinfo("完成", "历史记录已清空", parent=self._dialog)

    def _show_detail(self, event: object = None) -> None:
        """双击查看详细翻译内容。"""
        sel = self._tree.selection()
        if not sel:
            return

        values = self._tree.item(sel[0], "values")
        if not values:
            return

        # 根据选择的条目查找对应的 HistoryEntry
        matches = self._manager.list_entries(limit=500)
        for entry in matches:
            if entry.timestamp.startswith(values[0]):
                self._show_detail_window(entry)
                return

    def _show_detail_window(self, entry) -> None:
        """显示翻译详情窗口。"""
        detail = tk.Toplevel(self._dialog)
        detail.title("翻译详情")
        detail.geometry("500x350")
        detail.transient(self._dialog)
        detail.grab_set()

        # 元数据
        meta_text = (
            f"时间: {entry.timestamp[:19]}\n"
            f"模型: {entry.model}\n"
            f"方向: {entry.source_lang} → {entry.target_lang}\n"
        )
        if entry.detected_lang:
            meta_text += f"检测到: {entry.detected_lang}\n"
        if entry.duration_ms > 0:
            meta_text += f"耗时: {entry.duration_ms:.0f}ms\n"

        ttk.Label(detail, text=meta_text, justify=tk.LEFT).pack(
            padx=15, pady=(10, 5), anchor=tk.W
        )

        # 原文
        ttk.Label(detail, text="原文:", font=("", 10, "bold")).pack(
            padx=15, pady=(5, 0), anchor=tk.W
        )
        src_text = tk.Text(detail, height=4, wrap=tk.WORD, padx=5, pady=5)
        src_text.insert("1.0", entry.source_text)
        src_text.configure(state=tk.DISABLED)
        src_text.pack(fill=tk.X, padx=15, pady=2)

        # 译文
        ttk.Label(detail, text="译文:", font=("", 10, "bold")).pack(
            padx=15, pady=(5, 0), anchor=tk.W
        )
        tgt_text = tk.Text(detail, height=4, wrap=tk.WORD, padx=5, pady=5)
        tgt_text.insert("1.0", entry.target_text)
        tgt_text.configure(state=tk.DISABLED)
        tgt_text.pack(fill=tk.X, padx=15, pady=2)

        ttk.Button(detail, text="关闭", command=detail.destroy).pack(pady=10)

    # ------------------------------------------------------------------
    # 外部接口
    # ------------------------------------------------------------------

    def wait(self) -> None:
        """等待对话框关闭。"""
        self._dialog.wait_window()