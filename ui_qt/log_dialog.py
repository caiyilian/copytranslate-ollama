"""PyQt6 日志查看对话框。"""
from __future__ import annotations
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)
from core.log_viewer import read_logs

class LogDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("日志")
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        entries = read_logs(limit=500)
        content = "\n".join(
            f"{e.timestamp} [{e.level}] {e.message}" for e in entries
        )
        self._text.setPlainText(content or "(无日志)")
        layout.addWidget(self._text)
        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)