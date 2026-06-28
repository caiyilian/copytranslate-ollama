"""PyQt6 导出对话框。"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QSpinBox, QVBoxLayout, QWidget,
)
from core.export import export_entries, get_export_entries
from core.logger import HistoryManager

class ExportDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("导出翻译记录")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._limit_spin = QSpinBox()
        self._limit_spin.setRange(1, 10000)
        self._limit_spin.setValue(100)
        form.addRow("导出条数:", self._limit_spin)
        self._fmt_combo = QComboBox()
        self._fmt_combo.addItems(["txt", "csv", "json"])
        form.addRow("格式:", self._fmt_combo)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._do_export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _do_export(self) -> None:
        ext = self._fmt_combo.currentText()
        path, _ = QFileDialog.getSaveFileName(self, "保存导出", "", f"*.{ext}")
        if path:
            hm = HistoryManager()
            entries = get_export_entries(hm, limit=self._limit_spin.value())
            success = export_entries(entries, Path(path), fmt=ext)
            from PyQt6.QtWidgets import QMessageBox
            if success:
                QMessageBox.information(self, "导出完成", f"已导出 {len(entries)} 条记录")
            else:
                QMessageBox.critical(self, "导出失败", "无法写入文件")
            self.accept()