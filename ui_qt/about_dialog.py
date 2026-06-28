"""PyQt6 关于对话框。"""
from __future__ import annotations
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QLabel, QPushButton, QVBoxLayout, QWidget,
)
from PyQt6 import QtCore

class AboutDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setMinimumWidth(350)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("CopyTranslator-Ollama"))
        import sys
        layout.addWidget(QLabel(f"Python: {sys.version.split()[0]}"))
        layout.addWidget(QLabel(f"PyQt6: {QtCore.QT_VERSION_STR}"))
        layout.addWidget(QLabel("基于本地 Ollama 翻译模型的桌面翻译助手"))
        layout.addWidget(QLabel("https://github.com/caiyilian/copytranslate-ollama"))
        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)