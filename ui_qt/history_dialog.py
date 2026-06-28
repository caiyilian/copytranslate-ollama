"""PyQt6 翻译历史对话框。"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.logger import HistoryManager
from .detail_dialog import DetailDialog


class HistoryDialog(QWidget):
    """翻译历史对话框。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self._manager = HistoryManager()

        self.setWindowTitle("翻译历史")
        self.setMinimumSize(700, 450)
        self.resize(700, 450)

        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 搜索栏
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索:"))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("搜索原文或译文...")
        self._search_input.textChanged.connect(self._refresh)
        search_layout.addWidget(self._search_input)

        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh)
        search_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("清空历史")
        clear_btn.clicked.connect(self._do_clear)
        search_layout.addWidget(clear_btn)
        layout.addLayout(search_layout)

        # 表格
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["时间", "模型", "方向", "原文", "译文"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self._table.setColumnWidth(0, 150)
        self._table.setColumnWidth(1, 120)
        self._table.setColumnWidth(2, 80)
        self._table.setColumnWidth(3, 200)
        self._table.itemDoubleClicked.connect(self._show_detail)
        layout.addWidget(self._table, stretch=1)

        # 底部统计 + 复制按钮
        bottom_layout = QHBoxLayout()
        self._count_label = QLabel("共 0 条记录")
        bottom_layout.addWidget(self._count_label)

        bottom_layout.addStretch()

        for text, slot in [
            ("复制原文", self._copy_source),
            ("复制译文", self._copy_target),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            bottom_layout.addWidget(btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(close_btn)
        layout.addLayout(bottom_layout)

    def _refresh(self) -> None:
        """刷新列表。"""
        self._table.setRowCount(0)

        keyword = self._search_input.text().strip()
        if keyword:
            entries = self._manager.search(keyword)
        else:
            entries = self._manager.list_entries(limit=200)

        self._table.setRowCount(len(entries))
        for i, entry in enumerate(entries):
            self._table.setItem(i, 0, QTableWidgetItem(entry.timestamp[:19]))
            self._table.setItem(i, 1, QTableWidgetItem(entry.model))
            self._table.setItem(i, 2, QTableWidgetItem(f"{entry.source_lang}→{entry.target_lang}"))
            self._table.setItem(i, 3, QTableWidgetItem(entry.source_text[:80].replace("\n", " ")))
            self._table.setItem(i, 4, QTableWidgetItem(entry.target_text[:80].replace("\n", " ")))

        total = self._manager.count()
        shown = len(entries)
        self._count_label.setText(
            f"共 {total} 条记录" + (f" (显示 {shown})" if shown < total else "")
        )

    def _do_clear(self) -> None:
        """清空所有历史记录。"""
        from PyQt6.QtWidgets import QMessageBox

        if not self._manager.count():
            QMessageBox.information(self, "提示", "历史记录已为空")
            return
        confirm = QMessageBox.question(
            self, "确认清空", "确定清空所有翻译历史记录吗？\n此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._manager.clear()
            self._refresh()

    def _get_selected_entry(self):
        """获取选中的条目。"""
        row = self._table.currentRow()
        if row < 0:
            return None
        keyword = self._search_input.text().strip()
        if keyword:
            entries = self._manager.search(keyword)
        else:
            entries = self._manager.list_entries(limit=200)
        if row < len(entries):
            return entries[row]
        return None

    def _show_detail(self) -> None:
        """显示翻译详情。"""
        entry = self._get_selected_entry()
        if entry:
            dialog = DetailDialog(self, entry)
            dialog.exec()

    def _copy_source(self) -> None:
        """复制原文。"""
        entry = self._get_selected_entry()
        if entry:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(entry.source_text)

    def _copy_target(self) -> None:
        """复制译文。"""
        entry = self._get_selected_entry()
        if entry:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(entry.target_text)