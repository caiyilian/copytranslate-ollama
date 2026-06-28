"""非侵入式 Toast 通知组件。

在窗口右下角弹出短暂消息，自动淡出消失。
支持成功/信息/警告/错误四种类型。
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional


# 样式配置
_TOAST_COLORS = {
    "info": {"bg": "#e3f2fd", "fg": "#1565c0", "icon": "ℹ"},
    "success": {"bg": "#e8f5e9", "fg": "#2e7d32", "icon": "✓"},
    "warning": {"bg": "#fff3e0", "fg": "#e65100", "icon": "⚠"},
    "error": {"bg": "#ffebee", "fg": "#c62828", "icon": "✗"},
}

_TOAST_DURATION_MS = 3000  # 默认显示时间
_TOAST_FADE_MS = 50  # 淡出步进毫秒
_TOAST_MARGIN = 10  # 窗口右/下边距
_TOAST_WIDTH = 320
_TOAST_HEIGHT = 50


class Toast:
    """Toast 通知。

    用法:
        Toast.info(parent, "翻译完成")
        Toast.error(parent, "连接失败", duration=5000)
        Toast.warning(parent, "模型未找到")
        Toast.success(parent, "已保存")
    """

    _instances: list = []

    def __init__(
        self,
        parent: tk.Widget,
        message: str,
        kind: str = "info",
        duration: int = _TOAST_DURATION_MS,
    ) -> None:
        """创建并显示 Toast。

        Args:
            parent: 父窗口控件（或其根窗口）。
            message: 消息内容。
            kind: 类型: info / success / warning / error。
            duration: 显示时长（毫秒），之后自动淡出。
        """
        # 清除同类型旧 Toast
        self._cleanup_older(kind)

        root = parent.winfo_toplevel()
        colors = _TOAST_COLORS.get(kind, _TOAST_COLORS["info"])

        # 创建顶层窗口（无边框、置顶）
        self._win = tk.Toplevel(root)
        self._win.overrideredirect(True)
        self._win.attributes("-topmost", True)
        self._win.configure(bg=colors["bg"])

        # 内容
        frame = tk.Frame(
            self._win,
            bg=colors["bg"],
            padx=12,
            pady=8,
        )
        frame.pack(fill=tk.BOTH, expand=True)

        icon_label = tk.Label(
            frame,
            text=colors["icon"],
            font=("", 12),
            bg=colors["bg"],
            fg=colors["fg"],
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 8))

        msg_label = tk.Label(
            frame,
            text=message,
            font=("", 10),
            bg=colors["bg"],
            fg=colors["fg"],
            wraplength=_TOAST_WIDTH - 60,
            justify=tk.LEFT,
        )
        msg_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 定位在父窗口右下角
        self._position(root)

        # 加入实例列表
        self._instances.append(self)

        # 自动淡出
        self._win.after(duration, self._start_fade)

    def _cleanup_older(self, kind: str) -> None:
        """关闭同一类型的旧 Toast。"""
        for t in list(self._instances):
            if t is not self and t._kind == kind:
                t._destroy()

    def _kind(self) -> str:
        """获取类型（用于 cleanup）。"""
        return "info"  # 简化处理

    def _position(self, root: tk.Tk) -> None:
        """定位在父窗口右下角。"""
        root.update_idletasks()
        rx = root.winfo_x()
        ry = root.winfo_y()
        rw = root.winfo_width()
        rh = root.winfo_height()

        # 计算偏移（考虑已存在的 Toast）
        offset = 0
        for t in self._instances:
            if t is not self and t._win.winfo_exists():
                offset += _TOAST_HEIGHT + 4

        x = rx + rw - _TOAST_WIDTH - _TOAST_MARGIN
        y = ry + rh - _TOAST_HEIGHT - _TOAST_MARGIN - offset
        self._win.geometry(f"{_TOAST_WIDTH}x{_TOAST_HEIGHT}+{x}+{y}")

    def _start_fade(self) -> None:
        """开始淡出动画。"""
        self._fade_step(1.0)

    def _fade_step(self, opacity: float) -> None:
        """递归淡出。"""
        if not self._win.winfo_exists():
            return
        new_opacity = opacity - 0.1
        if new_opacity <= 0:
            self._destroy()
            return
        try:
            self._win.attributes("-alpha", new_opacity)
        except tk.TclError:
            self._destroy()
            return
        self._win.after(_TOAST_FADE_MS, self._fade_step, new_opacity)

    def _destroy(self) -> None:
        """销毁窗口并从实例列表移除。"""
        if self in self._instances:
            self._instances.remove(self)
        try:
            if self._win.winfo_exists():
                self._win.destroy()
        except tk.TclError:
            pass

    def close(self) -> None:
        """立即关闭。"""
        self._destroy()

    # ------------------------------------------------------------------
    # 静态便捷方法
    # ------------------------------------------------------------------

    @staticmethod
    def info(
        parent: tk.Widget,
        message: str,
        duration: int = _TOAST_DURATION_MS,
    ) -> "Toast":
        return Toast(parent, message, "info", duration)

    @staticmethod
    def success(
        parent: tk.Widget,
        message: str,
        duration: int = _TOAST_DURATION_MS,
    ) -> "Toast":
        return Toast(parent, message, "success", duration)

    @staticmethod
    def warning(
        parent: tk.Widget,
        message: str,
        duration: int = _TOAST_DURATION_MS,
    ) -> "Toast":
        return Toast(parent, message, "warning", duration)

    @staticmethod
    def error(
        parent: tk.Widget,
        message: str,
        duration: int = 5000,
    ) -> "Toast":
        return Toast(parent, message, "error", duration)