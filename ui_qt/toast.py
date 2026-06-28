"""PyQt6 Toast 通知组件。"""
from __future__ import annotations
from typing import Optional
from PyQt6.QtCore import QPropertyAnimation, QPoint, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

_STYLES = {
    "success": "background-color: #4caf50; color: white; padding: 10px 20px; border-radius: 4px;",
    "error": "background-color: #f44336; color: white; padding: 10px 20px; border-radius: 4px;",
    "info": "background-color: #2196f3; color: white; padding: 10px 20px; border-radius: 4px;",
}

class Toast(QWidget):
    """非侵入式通知。"""
    def __init__(self, parent: QWidget, message: str, style_type: str = "info") -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(_STYLES.get(style_type, _STYLES["info"]))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(message)
        label.setStyleSheet("color: white; font-size: 10pt;")
        layout.addWidget(label)
        self.adjustSize()

        # Position bottom-right of parent
        parent_rect = parent.geometry()
        self.move(parent_rect.right() - self.width() - 20, parent_rect.bottom() - self.height() - 40)
        self.show()

        # Auto-close after 3s
        QTimer.singleShot(3000, self.close)

    @staticmethod
    def fire(parent: QWidget, message: str, style: str = "info") -> None:
        Toast(parent, message, style)

    @staticmethod
    def success(parent: QWidget, message: str) -> None:
        Toast(parent, message, "success")

    @staticmethod
    def error(parent: QWidget, message: str) -> None:
        Toast(parent, message, "error")

    @staticmethod
    def info(parent: QWidget, message: str) -> None:
        Toast(parent, message, "info")