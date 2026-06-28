"""PyQt6 对照模式主窗口。

包含菜单栏、状态栏和基础框架，后续阶段逐步添加翻译组件。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QWidget,
)


class MainWindow(QMainWindow):
    """对照模式主窗口。"""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("CopyTranslator-Ollama")
        self.setMinimumSize(600, 350)
        self.resize(900, 550)

        self._build_menus()
        self._build_status_bar()
        self._build_central()

    # ------------------------------------------------------------------
    # 菜单栏
    # ------------------------------------------------------------------

    def _build_menus(self) -> None:
        """构建菜单栏。"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")

        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        focus_action = QAction("专注模式(&F)", self)
        focus_action.setEnabled(False)  # Phase 9 实现
        view_menu.addAction(focus_action)

    # ------------------------------------------------------------------
    # 状态栏
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        """构建状态栏。"""
        status_bar = self.statusBar()
        status_bar.showMessage("就绪")

    # ------------------------------------------------------------------
    # 中央区域
    # ------------------------------------------------------------------

    def _build_central(self) -> None:
        """构建中央区域（占位，后续阶段填充）。"""
        central = QWidget()
        self.setCentralWidget(central)

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def closeEvent(self, event):  # type: ignore
        """窗口关闭事件。"""
        from core.pipeline import Pipeline

        pipeline = getattr(self, "_pipeline", None)
        if pipeline:
            pipeline.close()
        event.accept()