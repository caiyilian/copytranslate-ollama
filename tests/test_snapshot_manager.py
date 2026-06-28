"""SnapshotManager 单元测试。"""

from unittest.mock import MagicMock, patch

from core.config import AppConfig, SnapshotConfig
from core.snapshot_manager import SnapshotManager, SnapshotError


class TestSnapshotManager:
    """测试快照的增删改查和应用。"""

    def setup_method(self) -> None:
        """每个测试前创建干净的 SnapshotManager。"""
        # 使用 patch.object 类级别打桩 save，避免 Pydantic v2 限制
        self._save_patch = patch.object(AppConfig, "save", MagicMock())
        self._save_patch.start()

        self._config = AppConfig(
            snapshots=[
                SnapshotConfig(
                    name="论文阅读",
                    model="translategemma:4b",
                    source_lang="en",
                    target_lang="zh",
                    mode="focus",
                ),
                SnapshotConfig(
                    name="快速浏览",
                    model="ali6parmak/hy-mt1.5:1.8b",
                    source_lang="auto",
                    target_lang="zh",
                    mode="contrast",
                ),
            ]
        )
        self._manager = SnapshotManager(self._config)

    def teardown_method(self) -> None:
        """清理 patch。"""
        self._save_patch.stop()

    def test_list_snapshots(self) -> None:
        """列出所有快照。"""
        snaps = self._manager.list_snapshots()
        assert len(snaps) == 2
        assert snaps[0].name == "论文阅读"

    def test_snapshot_names(self) -> None:
        """列出快照名称。"""
        names = self._manager.snapshot_names()
        assert names == ["论文阅读", "快速浏览"]

    def test_get_snapshot_exists(self) -> None:
        """获取存在的快照。"""
        snap = self._manager.get_snapshot("论文阅读")
        assert snap is not None
        assert snap.model == "translategemma:4b"

    def test_get_snapshot_not_exists(self) -> None:
        """获取不存在的快照返回 None。"""
        snap = self._manager.get_snapshot("不存在的")
        assert snap is None

    def test_add_snapshot_new(self) -> None:
        """添加新快照。"""
        self._manager.add_snapshot(
            SnapshotConfig(
                name="科技翻译",
                model="translategemma:4b",
                source_lang="en",
                target_lang="zh",
                mode="contrast",
            )
        )
        assert len(self._manager.list_snapshots()) == 3

    def test_add_snapshot_override(self) -> None:
        """添加同名快照覆盖旧的。"""
        self._manager.add_snapshot(
            SnapshotConfig(
                name="论文阅读",
                model="new-model",
                source_lang="en",
                target_lang="de",
                mode="contrast",
            )
        )
        snaps = self._manager.list_snapshots()
        assert len(snaps) == 2  # 不增加数量
        assert self._manager.get_snapshot("论文阅读").model == "new-model"

    def test_remove_snapshot_exists(self) -> None:
        """删除存在的快照。"""
        result = self._manager.remove_snapshot("论文阅读")
        assert result is True
        assert len(self._manager.list_snapshots()) == 1

    def test_remove_snapshot_not_exists(self) -> None:
        """删除不存在的快照返回 False。"""
        result = self._manager.remove_snapshot("不存在的")
        assert result is False
        assert len(self._manager.list_snapshots()) == 2

    def test_apply_snapshot(self) -> None:
        """应用快照到配置。"""
        target = AppConfig()  # 默认配置
        success = self._manager.apply_snapshot("论文阅读", target)
        assert success
        assert target.translation.active_model == "translategemma:4b"
        assert target.translation.source_lang == "en"
        assert target.translation.target_lang == "zh"
        assert target.output.show_mode == "focus"

    def test_apply_snapshot_not_found(self) -> None:
        """应用不存在的快照返回 False。"""
        target = AppConfig()
        success = self._manager.apply_snapshot("不存在的", target)
        assert success is False

    def test_save_current_as_new(self) -> None:
        """保存当前配置为新快照。"""
        self._manager.save_current_as("代码翻译", self._config)
        assert self._manager.get_snapshot("代码翻译") is not None
        assert len(self._manager.list_snapshots()) == 3

    def test_save_current_as_override(self) -> None:
        """使用 override 覆盖已有快照。"""
        self._manager.save_current_as(
            "论文阅读", self._config, override=True
        )
        assert len(self._manager.list_snapshots()) == 2  # 不增加

    def test_save_current_as_no_override_raises(self) -> None:
        """不使用 override 时同名抛出异常。"""
        try:
            self._manager.save_current_as("论文阅读", self._config)
            assert False, "应当抛出 SnapshotError"
        except SnapshotError:
            pass