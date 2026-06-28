"""PyQt6 系统托盘。

使用 QSystemTrayIcon 实现常驻托盘图标和右键菜单。
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon


def _create_icon() -> QIcon:
    """生成一个简单蓝色方块作为托盘图标。"""
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.blue)
    return QIcon(pixmap)


class SystemTray(QSystemTrayIcon):
    """系统托盘图标。

    用法:
        tray = SystemTray(on_show=..., on_quit=...)
        tray.setup()
    """

    def __init__(
        self,
        tooltip: str = "CopyTranslator-Ollama",
        on_show: Optional[Callable[[], None]] = None,
        on_focus: Optional[Callable[[], None]] = None,
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_switch_model: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()

        self._tooltip = tooltip
        self._on_show = on_show
        self._on_focus = on_focus
        self._on_toggle_pause = on_toggle_pause
        self._on_switch_model = on_switch_model
        self._on_quit = on_quit

        self.setIcon(_create_icon())
        self.setToolTip(tooltip)

        self._build_menu()
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        """构建右键菜单。"""
        menu = QMenu()

        self._show_action = QAction("显示/隐藏窗口", menu)
        self._show_action.triggered.connect(
            lambda: self._on_show() if self._on_show else None
        )
        menu.addAction(self._show_action)

        self._focus_action = QAction("专注模式", menu)
        self._focus_action.triggered.connect(
            lambda: self._on_focus() if self._on_focus else None
        )
        menu.addAction(self._focus_action)

        menu.addSeparator()

        self._pause_action = QAction("暂停监听", menu)
        self._pause_action.triggered.connect(
            lambda: self._on_toggle_pause() if self._on_toggle_pause else None
        )
        menu.addAction(self._pause_action)

        self._switch_action = QAction("切换模型", menu)
        self._switch_action.triggered.connect(
            lambda: self._on_switch_model() if self._on_switch_model else None
        )
        menu.addAction(self._switch_action)

        menu.addSeparator()

        self._quit_action = QAction("退出", menu)
        self._quit_action.triggered.connect(
            lambda: self._on_quit() if self._on_quit else None
        )
        menu.addAction(self._quit_action)

        self.setContextMenu(menu)

    def _on_activated(self, reason: int) -> None:
        """托盘图标点击事件。"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self._on_show:
                self._on_show()

    def set_pause_text(self, paused: bool) -> None:
        """更新暂停/恢复菜单文字。"""
        self._pause_action.setText("恢复监听" if paused else "暂停监听")