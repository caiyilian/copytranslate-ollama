"""PyQt6 配置快照管理对话框。"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig
from core.snapshot_manager import SnapshotManager


class SnapshotDialog(QDialog):
    """快照管理对话框。"""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        config: Optional[AppConfig] = None,
        on_select: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(parent)

        self._config = config or AppConfig.load()
        self._manager = SnapshotManager(self._config)
        self._on_select = on_select

        self.setWindowTitle("配置快照管理")
        self.setMinimumWidth(480)
        self.setMinimumHeight(380)

        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        QLabel("快照是可切换的翻译配置预设，包含模型、语言方向、模式等设置。").setWordWrap(True)
        layout.addWidget(QLabel("快照是可切换的翻译配置预设，包含模型、语言方向、模式等设置。"))

        # 列表
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._do_load)
        layout.addWidget(self._list, stretch=1)

        # 按钮
        btn_layout = QHBoxLayout()
        for text, slot in [
            ("加载", self._do_load),
            ("保存当前", self._do_save),
            ("删除", self._do_delete),
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def _refresh_list(self) -> None:
        self._list.clear()
        for snap in self._manager.list_snapshots():
            self._list.addItem(
                f"{snap.name}  [{snap.model}]  {snap.source_lang}→{snap.target_lang}  ({snap.mode})"
            )

    def _get_selected_name(self) -> Optional[str]:
        item = self._list.currentItem()
        if not item:
            QMessageBox.warning(self, "提示", "请先选择一个快照")
            return None
        return self._manager.list_snapshots()[self._list.currentRow()].name

    def _do_load(self) -> None:
        name = self._get_selected_name()
        if name is None:
            return
        success = self._manager.apply_snapshot(name, self._config)
        if success:
            self._config.save()
            if self._on_select:
                self._on_select(name)
            self.accept()
        else:
            QMessageBox.critical(self, "错误", f"无法加载快照 '{name}'")

    def _do_save(self) -> None:
        name, ok = QInputDialog.getText(self, "保存快照", "快照名称：")
        if not ok or not name:
            return
        try:
            self._manager.save_current_as(name, self._config, override=True)
            self._refresh_list()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _do_delete(self) -> None:
        name = self._get_selected_name()
        if name is None:
            return
        confirm = QMessageBox.question(
            self, "确认删除", f"确定删除快照 '{name}' 吗？"
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._manager.remove_snapshot(name)
            self._refresh_list()