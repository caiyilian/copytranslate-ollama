"""配置导入导出模块。

允许用户将当前配置（含快照）导出为 JSON 文件，或从 JSON 文件导入。
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from core.config import AppConfig


def export_config(config: AppConfig, file_path: Path) -> bool:
    """将配置导出到 JSON 文件。

    导出的数据包含元信息（导出时间、版本）和完整配置内容。

    Args:
        config: 当前配置对象。
        file_path: 目标文件路径（如 ~/Desktop/config_backup.json）。

    Returns:
        True 如果写入成功。
    """
    data: Dict[str, Any] = {
        "_meta": {
            "exported_at": datetime.now().isoformat(),
            "version": config.version,
            "app": "CopyTranslator-Ollama",
        },
        "config": json.loads(config.model_dump_json()),
    }
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def import_config(file_path: Path) -> Optional[AppConfig]:
    """从 JSON 文件导入配置。

    Args:
        file_path: 源文件路径。

    Returns:
        解析后的 AppConfig，如果文件无效返回 None。
    """
    if not file_path.exists():
        return None
    try:
        raw = file_path.read_text(encoding="utf-8")
        data: Dict[str, Any] = json.loads(raw)

        # 支持两种格式：带 _meta 包裹 或 裸 config
        if "config" in data:
            config_data = data["config"]
        else:
            config_data = data

        return AppConfig(**config_data)
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return None


def merge_config(target: AppConfig, source: AppConfig) -> AppConfig:
    """将 source 的非默认设置合并到 target。

    策略：对于每个子配置（translation/clipboard/cleaner 等），
    如果 source 中的值与 target 的默认值不同，则保留 source 的值。

    Args:
        target: 当前配置（接收合并）。
        source: 导入的配置。

    Returns:
        合并后的新 AppConfig。
    """
    # 从 target 的默认值克隆一份
    merged = target.model_copy(deep=True)

    # 翻译配置
    if source.translation.active_model != "translategemma:4b":
        merged.translation.active_model = source.translation.active_model
    if source.translation.source_lang != "auto":
        merged.translation.source_lang = source.translation.source_lang
    if source.translation.target_lang != "zh":
        merged.translation.target_lang = source.translation.target_lang
    if source.translation.temperature != 0.0:
        merged.translation.temperature = source.translation.temperature
    if source.translation.max_length != 2048:
        merged.translation.max_length = source.translation.max_length

    # 剪贴板配置
    if source.clipboard.poll_interval_ms != 300:
        merged.clipboard.poll_interval_ms = source.clipboard.poll_interval_ms
    if not source.clipboard.auto_translate:
        merged.clipboard.auto_translate = False
    if not source.clipboard.enable_cleaner:
        merged.clipboard.enable_cleaner = False

    # 净化配置
    if not source.cleaner.fix_hyphenation:
        merged.cleaner.fix_hyphenation = False
    if not source.cleaner.merge_paragraph_lines:
        merged.cleaner.merge_paragraph_lines = False
    if not source.cleaner.preserve_paragraph_breaks:
        merged.cleaner.preserve_paragraph_breaks = False

    # 输出配置
    if source.output.auto_copy_result:
        merged.output.auto_copy_result = True
    if source.output.auto_paste:
        merged.output.auto_paste = True
    if source.output.show_mode != "contrast":
        merged.output.show_mode = source.output.show_mode

    # 模型列表合并（去重）
    for model in source.models.available:
        if model not in merged.models.available:
            merged.models.available.append(model)

    # 快照合并（同名覆盖，新名追加）
    for snap in source.snapshots:
        existing = [s for s in merged.snapshots if s.name == snap.name]
        if existing:
            idx = merged.snapshots.index(existing[0])
            merged.snapshots[idx] = snap
        else:
            merged.snapshots.append(snap)

    return merged