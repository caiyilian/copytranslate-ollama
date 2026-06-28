"""PyQt6 翻译详情弹窗。"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DetailDialog(QDialog):
    """翻译详情对话框。"""

    def __init__(self, parent: QWidget, entry: Any) -> None:
        super().__init__(parent)
        self._entry = entry

        self.setWindowTitle("翻译详情")
        self.setMinimumSize(500, 350)
        self.resize(500, 350)

        layout = QVBoxLayout(self)

        # 元数据
        meta = (
            f"时间: {entry.timestamp[:19]}\n"
            f"模型: {entry.model}\n"
            f"方向: {entry.source_lang} → {entry.target_lang}\n"
        )
        if entry.detected_lang:
            meta += f"检测到: {entry.detected_lang}\n"
        if entry.duration_ms > 0:
            meta += f"耗时: {entry.duration_ms:.0f} ms\n"

        meta_label = QLabel(meta)
        meta_label.setWordWrap(True)
        layout.addWidget(meta_label)

        # 原文
        layout.addWidget(QLabel("原文:"))
        src_text = QTextEdit()
        src_text.setPlainText(entry.source_text)
        src_text.setReadOnly(True)
        src_text.setMaximumHeight(120)
        layout.addWidget(src_text)

        # 译文
        layout.addWidget(QLabel("译文:"))
        tgt_text = QTextEdit()
        tgt_text.setPlainText(entry.target_text)
        tgt_text.setReadOnly(True)
        tgt_text.setMaximumHeight(120)
        layout.addWidget(tgt_text)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)