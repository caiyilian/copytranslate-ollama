"""关于对话框。

展示应用版本、作者、许可证、GitHub 链接等信息。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

_VERSION = "0.1.0"
_AUTHOR = "caiyilian"
_GITHUB_URL = "https://github.com/caiyilian/copytranslate-ollama"
_LICENSE = "MIT"


class AboutDialog:
    """关于对话框。

    用法:
        dialog = AboutDialog(parent=root)
        dialog.wait()
    """

    def __init__(self, parent: tk.Widget) -> None:
        self._dialog = tk.Toplevel(parent)
        self._dialog.title("关于 CopyTranslator-Ollama")
        self._dialog.geometry("420x480")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        """构建界面。"""
        frame = ttk.Frame(self._dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # 图标/标题
        ttk.Label(
            frame,
            text="🌐",
            font=("", 36),
        ).pack(pady=(0, 10))

        ttk.Label(
            frame,
            text="CopyTranslator-Ollama",
            font=("", 16, "bold"),
        ).pack(pady=(0, 5))

        ttk.Label(
            frame,
            text=f"版本 {_VERSION}",
            font=("", 10),
        ).pack(pady=(0, 15))

        # 信息网格
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.X, pady=10)

        info_items = [
            ("作者", _AUTHOR),
            ("许可证", _LICENSE),
            ("平台", "Windows / macOS / Linux"),
            ("Python", "3.8+"),
        ]
        for i, (label, value) in enumerate(info_items):
            ttk.Label(
                info_frame,
                text=f"{label}:",
                font=("", 9, "bold"),
                width=10,
                anchor=tk.E,
            ).grid(row=i, column=0, pady=2, padx=(0, 10))
            ttk.Label(
                info_frame,
                text=value,
                font=("", 9),
            ).grid(row=i, column=1, pady=2, sticky=tk.W)

        # GitHub 链接
        ttk.Label(frame, text="GitHub:", font=("", 9, "bold")).pack(
            pady=(15, 3)
        )
        link = ttk.Label(
            frame,
            text=_GITHUB_URL,
            font=("", 9),
            foreground="blue",
            cursor="hand2",
        )
        link.pack()
        # 尝试绑定点击打开浏览器
        try:
            link.bind(
                "<Button-1>",
                lambda e: __import__("webbrowser").open(_GITHUB_URL),
            )
        except Exception:
            pass

        # 功能列表
        ttk.Label(frame, text="功能特性:", font=("", 9, "bold")).pack(
            pady=(15, 5)
        )
        features = [
            "• Ollama 本地模型翻译",
            "• 剪贴板监控自动翻译",
            "• 专注模式沉浸式翻译",
            "• 配置快照快速切换",
            "• 自动语言检测 (11种语言)",
            "• 翻译历史与统计",
            "• TXT/CSV/JSON 导出",
            "• 日志查看器",
            "• 自定义快捷键",
            "• 开机自启",
        ]
        for feat in features:
            ttk.Label(frame, text=feat, font=("", 9)).pack(anchor=tk.W)

        # 版权
        ttk.Label(
            frame,
            text=f"© 2025 {_AUTHOR}",
            font=("", 8),
            foreground="gray",
        ).pack(pady=(15, 0))

        # 关闭按钮
        ttk.Button(
            self._dialog,
            text="关闭",
            width=10,
            command=self._dialog.destroy,
        ).pack(pady=10)

    def wait(self) -> None:
        """等待对话框关闭。"""
        self._dialog.wait_window()