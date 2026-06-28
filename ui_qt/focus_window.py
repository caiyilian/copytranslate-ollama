"""PyQt6 专注模式浮窗。

无边框半透明浮窗，仅显示译文，支持拖拽、贴边隐藏和字体缩放。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QMouseEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig
from core.pipeline import Pipeline


# 贴边隐藏的像素阈值
_EDGE_SNAP_THRESHOLD = 30
# 贴边后露出的像素宽度
_EDGE_VISIBLE_WIDTH = 4


class FocusWindow(QWidget):
    """专注模式浮窗。"""

    def __init__(
        self,
        pipeline: Optional[Pipeline] = None,
        config: Optional[AppConfig] = None,
        main_window=None,
    ) -> None:
        super().__init__()

        self._pipeline = pipeline or Pipeline()
        self._config = config or AppConfig.load()
        self._main_window = main_window

        # 窗口属性
        self.setWindowTitle("CopyTranslator-Ollama — 专注模式")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setWindowOpacity(0.92)

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

        self._build_ui()
        self._restore_position()

    def _build_ui(self) -> None:
        """构建界面。"""
        self.setGeometry(self._win_x, self._win_y, self._window_width, self._window_height)

        # 主框架
        self._main_frame = QFrame(self)
        self._main_frame.setStyleSheet(
            "QFrame { background-color: #2b2b2b; border: 1px solid #555555; }"
        )
        self._main_frame.setGeometry(0, 0, self._window_width, self._window_height)

        layout = QVBoxLayout(self._main_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        title_bar = QFrame()
        title_bar.setStyleSheet("QFrame { background-color: #3c3c3c; }")
        title_bar.setFixedHeight(28)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(8, 0, 4, 0)

        title_label = QLabel("CopyTranslator-Ollama")
        title_label.setStyleSheet("color: #999999; font-size: 9pt;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self._switch_btn = QPushButton("\u25eb")  # ◫
        self._switch_btn.setFixedSize(24, 22)
        self._switch_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #aaaaaa; border: none; font-size: 12pt; }"
            "QPushButton:hover { color: #ffffff; }"
        )
        self._switch_btn.clicked.connect(self._switch_to_contrast)
        title_layout.addWidget(self._switch_btn)

        self._pause_btn = QPushButton("\u23f8")  # ⏸
        self._pause_btn.setFixedSize(24, 22)
        self._pause_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #cccccc; border: none; font-size: 10pt; }"
            "QPushButton:hover { color: #ffffff; }"
        )
        self._pause_btn.clicked.connect(self._toggle_pause)
        title_layout.addWidget(self._pause_btn)

        self._close_btn = QPushButton("\u2715")  # ✕
        self._close_btn.setFixedSize(24, 22)
        self._close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #cccccc; border: none; font-size: 10pt; }"
            "QPushButton:hover { color: #ff4444; }"
        )
        self._close_btn.clicked.connect(self._on_close)
        title_layout.addWidget(self._close_btn)

        layout.addWidget(title_bar)

        # 译文显示区域
        text_frame = QFrame()
        text_frame.setStyleSheet("QFrame { background-color: #2b2b2b; }")
        text_layout = QVBoxLayout(text_frame)
        text_layout.setContentsMargins(10, 10, 10, 10)

        self._trans_label = QLabel("等待翻译...")
        self._trans_label.setStyleSheet("color: #e0e0e0; background: transparent;")
        self._trans_label.setWordWrap(True)
        self._trans_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        font = QFont("Microsoft YaHei", self._font_size)
        self._trans_label.setFont(font)
        text_layout.addWidget(self._trans_label)

        layout.addWidget(text_frame, stretch=1)

        # 绑定拖拽事件到标题栏
        title_bar.mousePressEvent = self._on_drag_start
        title_bar.mouseMoveEvent = self._on_drag_move
        title_bar.mouseReleaseEvent = self._on_drag_end
        title_label.mousePressEvent = self._on_drag_start
        title_label.mouseMoveEvent = self._on_drag_move
        title_label.mouseReleaseEvent = self._on_drag_end

    # ------------------------------------------------------------------
    # 拖拽
    # ------------------------------------------------------------------

    def _on_drag_start(self, event: QMouseEvent) -> None:
        self._drag_start_x = event.globalPosition().x()
        self._drag_start_y = event.globalPosition().y()
        self._win_start_x = self._win_x
        self._win_start_y = self._win_y

    def _on_drag_move(self, event: QMouseEvent) -> None:
        dx = event.globalPosition().x() - self._drag_start_x
        dy = event.globalPosition().y() - self._drag_start_y
        self._win_x = int(self._win_start_x + dx)
        self._win_y = int(self._win_start_y + dy)
        self.move(self._win_x, self._win_y)

    def _on_drag_end(self, event: QMouseEvent) -> None:
        self._check_edge_snap()

    def _check_edge_snap(self) -> None:
        """检测屏幕边缘并贴边隐藏。"""
        screen = self.screen()
        if not screen:
            return
        screen_w = screen.availableGeometry().width()
        screen_h = screen.availableGeometry().height()

        snapped = False
        if self._win_y < _EDGE_SNAP_THRESHOLD:
            self._win_y = _EDGE_VISIBLE_WIDTH - self._window_height
            snapped = True
        elif self._win_y + self._window_height > screen_h - _EDGE_SNAP_THRESHOLD:
            self._win_y = screen_h - _EDGE_VISIBLE_WIDTH
            snapped = True
        if self._win_x < _EDGE_SNAP_THRESHOLD:
            self._win_x = _EDGE_VISIBLE_WIDTH - self._window_width
            snapped = True
        elif self._win_x + self._window_width > screen_w - _EDGE_SNAP_THRESHOLD:
            self._win_x = screen_w - _EDGE_VISIBLE_WIDTH
            snapped = True

        if snapped:
            self._hidden = True
            self.setWindowOpacity(0.3)
            self.move(self._win_x, self._win_y)

    # ------------------------------------------------------------------
    # 贴边弹出
    # ------------------------------------------------------------------

    def _show_from_edge(self) -> None:
        """从贴边状态弹出。"""
        if not self._hidden:
            return
        self._hidden = False
        self.setWindowOpacity(0.92)

        screen = self.screen()
        if not screen:
            return
        screen_w = screen.availableGeometry().width()
        screen_h = screen.availableGeometry().height()

        if self._win_y + self._window_height <= 0:
            self._win_y = 10
        elif self._win_x + self._window_width <= 0:
            self._win_x = 10
        elif self._win_y >= screen_h - _EDGE_VISIBLE_WIDTH:
            self._win_y = screen_h - self._window_height - 10
        elif self._win_x >= screen_w - _EDGE_VISIBLE_WIDTH:
            self._win_x = screen_w - self._window_width - 10

        self.move(self._win_x, self._win_y)

    # ------------------------------------------------------------------
    # 译文更新
    # ------------------------------------------------------------------

    def set_translation(self, text: str) -> None:
        """设置译文文本。"""
        self._show_from_edge()
        self._trans_label.setText(text)

    def set_status_text(self, text: str) -> None:
        """设置状态文本（翻译中/等待等）。"""
        self._trans_label.setText(text)

    # ------------------------------------------------------------------
    # 剪贴板控制
    # ------------------------------------------------------------------

    def _toggle_pause(self) -> None:
        """切换剪贴板监听。"""
        if hasattr(self, "_main_window") and self._main_window:
            self._main_window._toggle_clipboard_pause()
            self._pause_btn.setText("\u25b6" if self._main_window._clip_worker.is_paused else "\u23f8")

    # ------------------------------------------------------------------
    # 字体缩放
    # ------------------------------------------------------------------

    def wheelEvent(self, event) -> None:  # type: ignore
        """Ctrl+滚轮缩放字体。"""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._font_size = min(48, self._font_size + 2)
            else:
                self._font_size = max(8, self._font_size - 2)
            font = QFont("Microsoft YaHei", self._font_size)
            self._trans_label.setFont(font)
            event.accept()
        else:
            super().wheelEvent(event)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        """关闭浮窗，回到对照模式。"""
        self._switch_to_contrast()

    def _switch_to_contrast(self) -> None:
        """切换到对照模式。"""
        if self._main_window:
            self._main_window.show()
            self._main_window.raise_()
            self._main_window.activateWindow()
        self.close()

    def _restore_position(self) -> None:
        """恢复位置。"""
        self.move(self._win_x, self._win_y)