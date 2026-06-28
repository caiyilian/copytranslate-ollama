"""配置管理模块。

基于 Pydantic v2 的类型安全配置，支持 JSON 文件持久化。
首次运行自动在 ~/.copytranslate-ollama/config.json 生成默认配置。
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class CleanerConfig(BaseModel):
    """文本净化选项。"""

    fix_hyphenation: bool = Field(
        True, description="修复连字符断词 (transla-\\ntion -> translation)"
    )
    merge_paragraph_lines: bool = Field(
        True, description="合并段落内的换行"
    )
    preserve_paragraph_breaks: bool = Field(
        True, description="保留段落之间的空行分隔"
    )


class ClipboardConfig(BaseModel):
    """剪贴板管理配置。"""

    poll_interval_ms: int = Field(
        300, ge=50, le=5000, description="剪贴板轮询间隔(毫秒)"
    )
    auto_translate: bool = Field(True, description="检测到新内容自动翻译")
    enable_cleaner: bool = Field(True, description="启用文本净化")


class TranslationConfig(BaseModel):
    """翻译引擎配置。"""

    active_model: str = Field(
        "translategemma:4b", description="当前使用的翻译模型"
    )
    source_lang: str = Field("auto", description="源语言 (auto 自动检测)")
    target_lang: str = Field("zh", description="目标语言")
    temperature: float = Field(0.0, ge=0.0, le=2.0, description="温度参数")
    max_length: int = Field(2048, ge=64, le=8192, description="最大生成长度")


class OutputConfig(BaseModel):
    """输出配置。"""

    auto_copy_result: bool = Field(False, description="翻译完成后自动复制译文")
    auto_paste: bool = Field(False, description="自动粘贴替换选中文本")
    show_mode: str = Field("contrast", description="显示模式: contrast/focus")


class HotkeyConfig(BaseModel):
    """全局快捷键配置。"""

    toggle_window: str = Field("Ctrl+Shift+T", description="切换窗口显示/隐藏")
    switch_model: str = Field("Ctrl+Shift+M", description="切换翻译模型")
    toggle_mode: str = Field("Ctrl+Shift+F", description="切换对照/专注模式")
    manual_translate: str = Field("Ctrl+Shift+Enter", description="手动触发翻译")


class SnapshotConfig(BaseModel):
    """配置快照。"""

    name: str = Field(description="快照名称")
    model: str = Field(description="使用的模型")
    source_lang: str = "auto"
    target_lang: str = "zh"
    mode: str = "contrast"


class GeneralConfig(BaseModel):
    """通用配置。"""

    start_on_boot: bool = True
    minimize_to_tray: bool = True
    language: str = "zh-CN"


class ModelsConfig(BaseModel):
    """模型管理配置。"""

    available: List[str] = [
        "translategemma:4b",
        "ali6parmak/hy-mt1.5:1.8b",
    ]
    model_prompts: Dict[str, str] = {
        "translategemma:4b": "professional",
        "ali6parmak/hy-mt1.5:1.8b": "standard",
    }


class AppConfig(BaseModel):
    """顶层应用配置，合并所有子配置。"""

    version: int = Field(1, description="配置格式版本")
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    clipboard: ClipboardConfig = Field(default_factory=ClipboardConfig)
    cleaner: CleanerConfig = Field(default_factory=CleanerConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    hotkeys: HotkeyConfig = Field(default_factory=HotkeyConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    snapshots: List[SnapshotConfig] = Field(
        default_factory=lambda: [
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

    @staticmethod
    def get_config_dir() -> Path:
        """获取配置目录 (~/.copytranslate-ollama/)。"""
        return Path.home() / ".copytranslate-ollama"

    @staticmethod
    def get_config_path() -> Path:
        """获取配置文件路径。"""
        return AppConfig.get_config_dir() / "config.json"

    @classmethod
    def load(cls) -> "AppConfig":
        """从配置文件加载，不存在则创建默认配置。"""
        config_path = cls.get_config_path()
        if config_path.exists():
            raw = config_path.read_text(encoding="utf-8")
            data: Dict[str, Any] = json.loads(raw)
            return cls(**data)
        config = cls()
        config.save()
        return config

    def save(self) -> None:
        """保存配置到文件。"""
        config_dir = self.get_config_dir()
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = self.get_config_path()
        config_path.write_text(self._format_json(), encoding="utf-8")

    def _format_json(self) -> str:
        """格式化为美观的 JSON 字符串。"""
        data = json.loads(self.model_dump_json())
        return json.dumps(data, ensure_ascii=False, indent=2)