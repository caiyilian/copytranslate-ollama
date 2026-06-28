"""专注模式浮窗。

无边框半透明浮窗，仅显示译文，支持拖拽、贴边隐藏和字体缩放。
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from core.clipboard import ClipboardWatcher
from core.pipeline import Pipeline
from core.config import AppConfig


# 贴边隐藏的像素阈值
_EDGE_SNAP_THRESHOLD = 30
# 贴边后露出的像素宽度
_EDGE_VISIBLE_WIDTH = 4
# 剪贴板轮询间隔（毫秒）
_CLIPBOARD_POLL_MS = 500


class FocusWindow:
    """专注模式浮窗。

    无边框半透明，仅显示译文，支持拖拽移动和贴边隐藏。
    """

    def __init__(
        self,
        pipeline: Optional[Pipeline] = None,
        config: Optional[AppConfig] = None,
        main_window: Optional[Any] = None,
    ) -> None:
        self._pipeline = pipeline or Pipeline()
        self._config = config or AppConfig.load()
        self._main_window = main_window

        self._root = tk.Tk()
        self._root.title("CopyTranslator-Ollama — 专注模式")
        self._root.overrideredirect(True)  # 无边框
        self._root.attributes("-topmost", True)  # 置顶
        self._root.attributes("-alpha", 0.92)  # 半透明

        # 窗口尺寸
        self._window_width = 420
        self._window_height = 200
        self._font_size = 16

        # 位置
        self._win_x = 100
        self._win_y = 100
        self._hidden = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = 0
        self._win_start_y = 0

        # 剪贴板监听
        self._clip_watcher = ClipboardWatcher(
            callback=self._on_clipboard_change,
            config=self._config.clipboard,
        )
        self._clip_running = False
        self._clip_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._bind_events()
        self._restore_position()

    def _build_ui(self) -> None:
        """构建界面。"""
        # 主框架（带背景色，形成可见区域）
        self._main_frame = tk.Frame(
            self._root,
            bg="#2b2b2b",
            highlightbackground="#555555",
            highlightthickness=1,
        )
        self._main_frame.pack(fill=tk.BOTH, expand=True)

        # 顶栏（拖拽手柄 + 控制按钮）
        self._title_bar = tk.Frame(
            self._main_frame, bg="#3c3c3c", height=28
        )
        self._title_bar.pack(fill=tk.X)
        self._title_bar.pack_propagate(False)

        # 拖拽提示
        self._drag_label = tk.Label(
            self._title_bar,
            text="CopyTranslator-Ollama",
            bg="#3c3c3c",
            fg="#999999",
            font=("Microsoft YaHei", 9),
        )
        self._drag_label.pack(side=tk.LEFT, padx=8)

        # 控制按钮
        self._switch_btn = tk.Button(
            self._title_bar,
            text="◫",
            bg="#3c3c3c",
            fg="#aaaaaa",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            cursor="hand2",
            command=self._switch_to_contrast,
        )
        self._switch_btn.pack(side=tk.RIGHT, padx=(0, 2))

        self._pause_btn = tk.Button(
            self._title_bar,
            text="⏸",
            bg="#3c3c3c",
            fg="#cccccc",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            cursor="hand2",
            command=self._toggle_pause,
        )
        self._pause_btn.pack(side=tk.RIGHT, padx=(0, 4))

        self._close_btn = tk.Button(
            self._title_bar,
            text="✕",
            bg="#3c3c3c",
            fg="#cccccc",
            relief=tk.FLAT,
            font=("Segoe UI", 10),
            cursor="hand2",
            command=self._on_close,
        )
        self._close_btn.pack(side=tk.RIGHT, padx=(0, 4))

        # 译文显示区域
        self._text_frame = tk.Frame(
            self._main_frame, bg="#2b2b2b"
        )
        self._text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._trans_label = tk.Label(
            self._text_frame,
            text="等待翻译...",
            bg="#2b2b2b",
            fg="#e0e0e0",
            font=("Microsoft YaHei", self._font_size),
            wraplength=self._window_width - 40,
            justify=tk.LEFT,
            anchor=tk.NW,
        )
        self._trans_label.pack(fill=tk.BOTH, expand=True)

        # 设置窗口尺寸
        self._root.geometry(
            f"{self._window_width}x{self._window_height}"
        )

    # ------------------------------------------------------------------
    # 事件绑定
    # ------------------------------------------------------------------

    def _bind_events(self) -> None:
        """绑定事件。"""
        # 拖拽：绑定到标题栏
        for widget in (self._title_bar, self._drag_label):
            widget.bind("<Button-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_move)
            widget.bind("<ButtonRelease-1>", self._on_drag_end)

        # 字体缩放（Ctrl+滚轮）
        self._root.bind(
            "<Control-MouseWheel>", self._on_zoom
        )
        self._trans_label.bind(
            "<Control-MouseWheel>", self._on_zoom
        )

        # 窗口关闭
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # 拖拽
    # ------------------------------------------------------------------

    def _on_drag_start(self, event: tk.Event) -> None:
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        self._win_start_x = self._win_x
        self._win_start_y = self._win_y

    def _on_drag_move(self, event: tk.Event) -> None:
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        new_x = self._win_start_x + dx
        new_y = self._win_start_y + dy
        self._win_x = new_x
        self._win_y = new_y
        self._root.geometry(
            f"+{int(new_x)}+{int(new_y)}"
        )

    def _on_drag_end(self, event: tk.Event) -> None:
        """拖拽结束，检查是否需要贴边隐藏。"""
        self._check_edge_snap()

    def _check_edge_snap(self) -> None:
        """检测屏幕边缘并贴边隐藏。"""
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()

        snapped = False
        # 顶部贴边
        if self._win_y < _EDGE_SNAP_THRESHOLD:
            self._win_y = _EDGE_VISIBLE_WIDTH - self._window_height
            snapped = True
        # 底部贴边
        elif self._win_y + self._window_height > screen_h - _EDGE_SNAP_THRESHOLD:
            self._win_y = screen_h - _EDGE_VISIBLE_WIDTH
            snapped = True
        # 左侧贴边
        if self._win_x < _EDGE_SNAP_THRESHOLD:
            self._win_x = _EDGE_VISIBLE_WIDTH - self._window_width
            snapped = True
        # 右侧贴边
        elif self._win_x + self._window_width > screen_w - _EDGE_SNAP_THRESHOLD:
            self._win_x = screen_w - _EDGE_VISIBLE_WIDTH
            snapped = True

        if snapped:
            self._hidden = True
            self._root.attributes("-alpha", 0.3)
            self._root.geometry(
                f"+{int(self._win_x)}+{int(self._win_y)}"
            )

    # ------------------------------------------------------------------
    # 贴边弹出
    # ------------------------------------------------------------------

    def _show_from_edge(self) -> None:
        """从贴边状态弹出。"""
        if not self._hidden:
            return
        self._hidden = False
        self._root.attributes("-alpha", 0.92)

        # 恢复位置到可见区域
        screen_w = self._root.winfo_screenwidth()
        screen_h = self._root.winfo_screenheight()

        # 如果在顶部贴边
        if self._win_y + self._window_height <= 0:
            self._win_y = 10
        # 如果在左侧贴边
        elif self._win_x + self._window_width <= 0:
            self._win_x = 10
        # 如果在底部贴边
        elif self._win_y >= screen_h - _EDGE_VISIBLE_WIDTH:
            self._win_y = screen_h - self._window_height - 10
        # 如果在右侧贴边
        elif self._win_x >= screen_w - _EDGE_VISIBLE_WIDTH:
            self._win_x = screen_w - self._window_width - 10

        self._root.geometry(
            f"+{int(self._win_x)}+{int(self._win_y)}"
        )

    # ------------------------------------------------------------------
    # 字体缩放
    # ------------------------------------------------------------------

    def _on_zoom(self, event: tk.Event) -> None:
        """Ctrl+滚轮缩放字体。"""
        if event.delta > 0:
            self._font_size = min(48, self._font_size + 2)
        else:
            self._font_size = max(10, self._font_size - 2)
        self._trans_label.configure(
            font=("Microsoft YaHei", self._font_size)
        )

    # ------------------------------------------------------------------
    # 剪贴板监听
    # ------------------------------------------------------------------

    def _on_clipboard_change(self, text: str) -> None:
        """剪贴板变化回调（后台线程调用）。"""
        self._root.after(0, self._update_translation, text)

    def _update_translation(self, text: str) -> None:
        """翻译并更新显示（主线程）。"""
        # 从贴边状态弹出
        self._show_from_edge()

        self._trans_label.configure(text="翻译中...")
        self._root.update()

        try:
            result = self._pipeline.translate_once(
                text=text,
                source=self._config.translation.source_lang,
                target=self._config.translation.target_lang,
                model=self._config.translation.active_model,
            )
            self._trans_label.configure(text=result)
        except Exception as e:
            self._trans_label.configure(text=f"[错误] {e}")

    def _toggle_pause(self) -> None:
        """切换剪贴板监听。"""
        self._clip_paused = not self._clip_paused
        if self._clip_paused:
            self._pause_btn.configure(text="▶")
            self._trans_label.configure(text="(监听已暂停)")
        else:
            self._pause_btn.configure(text="⏸")
            self._trans_label.configure(text="等待翻译...")

    def _clipboard_loop(self) -> None:
        """后台剪贴板轮询。"""
        self._clip_running = True
        self._clip_paused = False
        while self._clip_running:
            try:
                text = self._clip_watcher.poll_once()
                if text is not None and not self._clip_paused:
                    self._on_clipboard_change(text)
            except Exception:
                pass
            import time
            time.sleep(_CLIPBOARD_POLL_MS / 1000.0)

    # ------------------------------------------------------------------
    # 位置持久化
    # ------------------------------------------------------------------

    def _restore_position(self) -> None:
        """恢复上次位置。"""
        self._root.geometry(
            f"+{self._win_x}+{self._win_y}"
        )

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def _start_clipboard_watch(self) -> None:
        """启动后台监听线程。"""
        self._clip_thread = threading.Thread(
            target=self._clipboard_loop,
            daemon=True,
            name="focus-clipboard",
        )
        self._clip_thread.start()

    def _stop_clipboard_watch(self) -> None:
        """停止后台监听。"""
        self._clip_running = False

    def _on_close(self) -> None:
        """关闭浮窗，回到对照模式或退出。"""
        self._stop_clipboard_watch()
        if self._main_window:
            self._main_window._show_window()
            self._root.destroy()
        else:
            self._pipeline.close()
            self._root.destroy()

    def _switch_to_contrast(self) -> None:
        """切换到对照模式。"""
        self._stop_clipboard_watch()
        if self._main_window:
            self._main_window._show_window()
        self._root.destroy()

    def run(self) -> None:
        """启动主循环。"""
        self._start_clipboard_watch()
        self._root.mainloop()