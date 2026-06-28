"""配置快照管理器。

提供快照的 CRUD 操作：列出、保存、加载、删除，并支持将快照应用于当前配置。
"""

from __future__ import annotations

from typing import List, Optional

from core.config import AppConfig, SnapshotConfig


class SnapshotError(Exception):
    """快照操作异常。"""


class SnapshotManager:
    """配置快照管理器。

    管理用户保存的翻译配置预设，每个快照包含模型、语言方向、模式等关键设置。
    快照数据保存在 AppConfig.snapshots 中，持久化到 config.json。
    """

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        self._config = config or AppConfig.load()

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_snapshots(self) -> List[SnapshotConfig]:
        """返回所有快照列表。"""
        return list(self._config.snapshots)

    def get_snapshot(self, name: str) -> Optional[SnapshotConfig]:
        """按名称查找快照。"""
        for s in self._config.snapshots:
            if s.name == name:
                return s
        return None

    def snapshot_names(self) -> List[str]:
        """返回所有快照名称。"""
        return [s.name for s in self._config.snapshots]

    # ------------------------------------------------------------------
    # 修改
    # ------------------------------------------------------------------

    def add_snapshot(self, snapshot: SnapshotConfig) -> None:
        """添加新快照（同名则覆盖）。"""
        self._remove_by_name(snapshot.name)
        self._config.snapshots.append(snapshot)
        self._config.save()

    def remove_snapshot(self, name: str) -> bool:
        """删除指定名称的快照。存在则删除并返回 True。"""
        removed = self._remove_by_name(name)
        if removed:
            self._config.save()
        return removed

    def _remove_by_name(self, name: str) -> bool:
        """内部：从列表移除同名快照。"""
        before = len(self._config.snapshots)
        self._config.snapshots = [
            s for s in self._config.snapshots if s.name != name
        ]
        return len(self._config.snapshots) < before

    # ------------------------------------------------------------------
    # 应用
    # ------------------------------------------------------------------

    def apply_snapshot(self, name: str, config: AppConfig) -> bool:
        """将命名快照的设置应用到传入的 config 对象。

        修改 config.translation 和 config.output 的对应字段。
        不自动保存——由调用方决定何时保存。

        Args:
            name: 快照名称。
            config: 要应用到的目标配置对象。

        Returns:
            True 如果快照存在并应用成功。
        """
        snapshot = self.get_snapshot(name)
        if snapshot is None:
            return False

        config.translation.active_model = snapshot.model
        config.translation.source_lang = snapshot.source_lang
        config.translation.target_lang = snapshot.target_lang
        config.output.show_mode = snapshot.mode

        return True

    # ------------------------------------------------------------------
    # 从当前配置创建快照
    # ------------------------------------------------------------------

    def save_current_as(
        self,
        name: str,
        config: AppConfig,
        override: bool = False,
    ) -> None:
        """将当前配置保存为快照。

        Args:
            name: 快照名称。
            config: 从中提取设置的配置对象。
            override: 如果 True，同名快照被覆盖；否则抛出 SnapshotError。

        Raises:
            SnapshotError: 同名已存在且 override=False。
        """
        if not override and self.get_snapshot(name) is not None:
            raise SnapshotError(f"快照 '{name}' 已存在")

        snapshot = SnapshotConfig(
            name=name,
            model=config.translation.active_model,
            source_lang=config.translation.source_lang,
            target_lang=config.translation.target_lang,
            mode=config.output.show_mode,
        )
        self.add_snapshot(snapshot)
