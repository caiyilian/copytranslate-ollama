"""翻译统计面板对话框。

展示翻译活动的统计数据：总数、字符数、模型使用频率、语言方向等。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.stats import TranslationStats, compute_stats


class StatsDialog:
    """翻译统计面板对话框。

    用法:
        dialog = StatsDialog(parent=root)
        dialog.wait()
    """

    def __init__(self, parent: tk.Widget) -> None:
        self._stats = compute_stats()

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("翻译统计")
        self._dialog.geometry("460x400")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        """构建界面。"""
        frame = ttk.Frame(self._dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)
        self._root = frame

        self._build_overview_section()
        self._build_model_section()
        self._build_language_section()

        # 刷新按钮
        btn_frame = ttk.Frame(self._dialog, padding="5")
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="刷新", command=self._refresh
        ).pack(side=tk.LEFT, padx=10)

        ttk.Label(
            btn_frame,
            text=f"更新于: {__import__('datetime').datetime.now():%H:%M:%S}",
            font=("", 8),
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            btn_frame, text="关闭", command=self._dialog.destroy
        ).pack(side=tk.RIGHT, padx=10)

    # ------------------------------------------------------------------
    # 各区块
    # ------------------------------------------------------------------

    def _add_section_title(self, text: str) -> None:
        """添加分段标题。"""
        ttk.Label(
            self._root,
            text=text,
            font=("", 11, "bold"),
            padding=(0, 8, 0, 4),
        ).pack(anchor=tk.W)

    def _add_stat_row(self, label: str, value: str) -> None:
        """添加单行统计显示。"""
        row = ttk.Frame(self._root)
        row.pack(fill=tk.X, pady=1)
        ttk.Label(row, text=label, width=28, anchor=tk.W).pack(side=tk.LEFT)
        ttk.Label(
            row, text=value, anchor=tk.W, font=("", 10)
        ).pack(side=tk.LEFT)

    def _build_overview_section(self) -> None:
        """概览统计区块。"""
        self._add_section_title("概览")
        s = self._stats
        self._add_stat_row("翻译总数", str(s.total_translations))
        self._add_stat_row("原文总字符数", f"{s.total_source_chars:,}")
        self._add_stat_row("译文总字符数", f"{s.total_target_chars:,}")
        self._add_stat_row("总耗时", f"{s.total_duration_ms / 1000:.1f} 秒")
        self._add_stat_row("平均耗时", f"{s.avg_duration_ms:.0f} ms/次")

    def _build_model_section(self) -> None:
        """模型使用统计。"""
        self._add_section_title("模型使用")
        s = self._stats
        if not s.model_counts:
            self._add_stat_row("（无数据）", "")
            return
        self._add_stat_row("最常用模型", s.top_model)
        for model, count in sorted(
            s.model_counts.items(),
            key=lambda x: -x[1],
        )[:5]:
            self._add_stat_row(f"  {model}", f"{count} 次")

    def _build_language_section(self) -> None:
        """语言方向统计。"""
        self._add_section_title("语言方向")
        s = self._stats
        has_source = bool(s.source_lang_counts)
        has_target = bool(s.target_lang_counts)

        if not has_source and not has_target:
            self._add_stat_row("（无数据）", "")
            return

        if has_source:
            self._add_stat_row("最常见源语言", s.top_source_lang)
            for lang, count in sorted(
                s.source_lang_counts.items(),
                key=lambda x: -x[1],
            )[:3]:
                self._add_stat_row(f"  {lang}", f"{count} 次")

        if has_target:
            self._add_stat_row("最常见目标语言", s.top_target_lang)
            for lang, count in sorted(
                s.target_lang_counts.items(),
                key=lambda x: -x[1],
            )[:3]:
                self._add_stat_row(f"  {lang}", f"{count} 次")

    def _refresh(self) -> None:
        """重新计算并刷新显示。"""
        self._stats = compute_stats()
        # 销毁并重建 UI
        self._root.destroy()
        self._build_ui()

    def wait(self) -> None:
        """等待对话框关闭。"""
        self._dialog.wait_window()