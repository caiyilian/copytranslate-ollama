"""PyQt6 翻译统计对话框。"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.stats import compute_stats


class StatsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("翻译统计")
        self.setMinimumWidth(350)

        stats = compute_stats()

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("翻译次数:", QLabel(str(stats.total_translations)))
        form.addRow("原文总字符:", QLabel(str(stats.total_source_chars)))
        form.addRow("译文总字符:", QLabel(str(stats.total_target_chars)))
        form.addRow("平均耗时:", QLabel(f"{stats.avg_duration_ms:.0f} ms"))
        form.addRow("最常用模型:", QLabel(stats.top_model))
        form.addRow("最常见源语言:", QLabel(stats.top_source_lang))
        form.addRow("最常见目标语言:", QLabel(stats.top_target_lang))
        layout.addLayout(form)

        btn = QPushButton("关闭")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
