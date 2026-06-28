"""Config IO 导入导出单元测试。"""

import json
import tempfile
from pathlib import Path

from core.config import AppConfig, SnapshotConfig
from core.config_io import export_config, import_config, merge_config


class TestExportImport:
    """测试配置的导出、导入和合并功能。"""

    def setup_method(self) -> None:
        self._tmp = tempfile.mktemp(suffix=".json")
        self._config = AppConfig()

    def teardown_method(self) -> None:
        Path(self._tmp).unlink(missing_ok=True)

    def test_export_creates_file(self) -> None:
        """导出应创建文件。"""
        result = export_config(self._config, Path(self._tmp))
        assert result is True
        assert Path(self._tmp).exists()

    def test_export_contains_meta(self) -> None:
        """导出文件应包含元信息。"""
        export_config(self._config, Path(self._tmp))
        data = json.loads(Path(self._tmp).read_text(encoding="utf-8"))
        assert "_meta" in data
        assert data["_meta"]["app"] == "CopyTranslator-Ollama"

    def test_export_contains_config(self) -> None:
        """导出文件应包含配置数据。"""
        export_config(self._config, Path(self._tmp))
        data = json.loads(Path(self._tmp).read_text(encoding="utf-8"))
        assert "config" in data
        assert "translation" in data["config"]

    def test_import_returns_config(self) -> None:
        """导入应返回 AppConfig。"""
        export_config(self._config, Path(self._tmp))
        imported = import_config(Path(self._tmp))
        assert imported is not None
        assert isinstance(imported, AppConfig)

    def test_import_preserves_values(self) -> None:
        """导入应保留导出的值。"""
        self._config.translation.active_model = "custom-model"
        self._config.translation.target_lang = "de"
        export_config(self._config, Path(self._tmp))
        imported = import_config(Path(self._tmp))
        assert imported is not None
        assert imported.translation.active_model == "custom-model"
        assert imported.translation.target_lang == "de"

    def test_import_nonexistent_file(self) -> None:
        """导入不存在的文件返回 None。"""
        result = import_config(Path("/nonexistent/file.json"))
        assert result is None

    def test_import_invalid_json(self) -> None:
        """导入无效的 JSON 返回 None。"""
        Path(self._tmp).write_text("{invalid", encoding="utf-8")
        result = import_config(Path(self._tmp))
        assert result is None

    def test_merge_preserves_target_defaults(self) -> None:
        """合并应保留 target 的默认值。"""
        target = AppConfig()
        source = AppConfig()
        merged = merge_config(target, source)
        assert merged.translation.active_model == "translategemma:4b"
        assert merged.translation.source_lang == "auto"

    def test_merge_takes_source_non_default(self) -> None:
        """合并应使用 source 的非默认值。"""
        target = AppConfig()
        source = AppConfig()
        source.translation.active_model = "other-model"
        source.translation.target_lang = "de"
        merged = merge_config(target, source)
        assert merged.translation.active_model == "other-model"
        assert merged.translation.target_lang == "de"

    def test_merge_model_list_dedup(self) -> None:
        """合并模型列表应去重。"""
        target = AppConfig()
        source = AppConfig()
        source.models.available = ["model-a", "model-b"]
        merged = merge_config(target, source)
        # "translategemma:4b" 和 "ali6parmak/hy-mt1.5:1.8b" 已经在 target 中
        assert "model-a" in merged.models.available
        assert "model-b" in merged.models.available

    def test_merge_snapshots_append(self) -> None:
        """合并应追加新快照。"""
        target = AppConfig()
        source = AppConfig()
        source.snapshots = [
            SnapshotConfig(
                name="new-snap",
                model="m",
                source_lang="en",
                target_lang="zh",
                mode="contrast",
            )
        ]
        merged = merge_config(target, source)
        names = [s.name for s in merged.snapshots]
        assert "new-snap" in names

    def test_merge_snapshots_override(self) -> None:
        """合并应覆盖同名快照。"""
        target = AppConfig()
        source = AppConfig()
        source.snapshots = [
            SnapshotConfig(
                name="论文阅读",
                model="new-model",
                source_lang="fr",
                target_lang="en",
                mode="focus",
            )
        ]
        merged = merge_config(target, source)
        snap = [s for s in merged.snapshots if s.name == "论文阅读"][0]
        assert snap.model == "new-model"