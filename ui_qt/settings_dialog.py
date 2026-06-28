"""PyQt6 设置面板。

按 Tab 分类组织翻译、剪贴板、净化、输出等配置项。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig

_LANG_DISPLAY = {
    "auto": "自动检测", "zh": "简体中文", "en": "English",
    "ja": "日本語", "ko": "한국어", "fr": "Français",
    "de": "Deutsch", "es": "Español", "ru": "Русский",
    "pt": "Português", "it": "Italiano", "vi": "Tiếng Việt", "th": "ไทย",
}
_LANG_CODE = {v: k for k, v in _LANG_DISPLAY.items()}


class SettingsDialog(QDialog):
    """设置面板对话框。"""

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        super().__init__(parent)

        self._config = config or AppConfig.load()
        self._original = self._config  # 保存引用

        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self._build_ui()
        self._load_config()

    def _build_ui(self) -> None:
        """构建 UI。"""
        layout = QVBoxLayout(self)

        # Tab 页
        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._build_translation_tab(), "翻译")
        tabs.addTab(self._build_clipboard_tab(), "剪贴板")
        tabs.addTab(self._build_cleaner_tab(), "净化")
        tabs.addTab(self._build_output_tab(), "输出")

        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # 翻译 Tab
    # ------------------------------------------------------------------

    def _build_translation_tab(self) -> QWidget:
        """翻译设置 Tab。"""
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(20, 15, 20, 15)

        # 模型选择
        self._model_combo = QComboBox()
        self._model_combo.addItems(self._config.models.available)
        form.addRow("模型:", self._model_combo)

        # 源语言
        self._source_combo = QComboBox()
        self._source_combo.addItems(list(_LANG_DISPLAY.values()))
        form.addRow("源语言:", self._source_combo)

        # 目标语言
        self._target_combo = QComboBox()
        tv = [v for k, v in _LANG_DISPLAY.items() if k != "auto"]
        self._target_combo.addItems(tv)
        form.addRow("目标语言:", self._target_combo)

        # 温度
        self._temp_spin = QDoubleSpinBox()
        self._temp_spin.setRange(0.0, 2.0)
        self._temp_spin.setSingleStep(0.1)
        self._temp_spin.setDecimals(1)
        form.addRow("温度:", self._temp_spin)

        # 最大长度
        self._maxlen_spin = QSpinBox()
        self._maxlen_spin.setRange(64, 8192)
        self._maxlen_spin.setSingleStep(128)
        form.addRow("最大长度:", self._maxlen_spin)

        return tab

    # ------------------------------------------------------------------
    # 剪贴板 Tab
    # ------------------------------------------------------------------

    def _build_clipboard_tab(self) -> QWidget:
        """剪贴板设置 Tab。"""
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(20, 15, 20, 15)

        self._poll_spin = QSpinBox()
        self._poll_spin.setRange(100, 5000)
        self._poll_spin.setSingleStep(100)
        self._poll_spin.setSuffix(" ms")
        form.addRow("轮询间隔:", self._poll_spin)

        self._auto_translate_cb = QCheckBox("自动翻译")
        form.addRow("", self._auto_translate_cb)

        self._enable_cleaner_cb = QCheckBox("启用文本净化")
        form.addRow("", self._enable_cleaner_cb)

        return tab

    # ------------------------------------------------------------------
    # 净化 Tab
    # ------------------------------------------------------------------

    def _build_cleaner_tab(self) -> QWidget:
        """净化设置 Tab。"""
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(20, 15, 20, 15)

        self._fix_hyphen_cb = QCheckBox("修复连字符断词")
        form.addRow("", self._fix_hyphen_cb)

        self._merge_lines_cb = QCheckBox("合并段落内换行")
        form.addRow("", self._merge_lines_cb)

        self._preserve_para_cb = QCheckBox("保留段落分隔")
        form.addRow("", self._preserve_para_cb)

        return tab

    # ------------------------------------------------------------------
    # 输出 Tab
    # ------------------------------------------------------------------

    def _build_output_tab(self) -> QWidget:
        """输出设置 Tab。"""
        tab = QWidget()
        form = QFormLayout(tab)
        form.setContentsMargins(20, 15, 20, 15)

        self._auto_copy_cb = QCheckBox("自动复制结果")
        form.addRow("", self._auto_copy_cb)

        self._auto_paste_cb = QCheckBox("自动粘贴")
        form.addRow("", self._auto_paste_cb)

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["contrast", "focus"])
        form.addRow("默认模式:", self._mode_combo)

        return tab

    # ------------------------------------------------------------------
    # 加载/保存
    # ------------------------------------------------------------------

    def _load_config(self) -> None:
        """从配置加载值到 UI。"""
        cfg = self._config.translation
        self._model_combo.setCurrentText(cfg.active_model)
        src = _LANG_DISPLAY.get(cfg.source_lang, cfg.source_lang)
        self._source_combo.setCurrentText(src)
        tgt = _LANG_DISPLAY.get(cfg.target_lang, cfg.target_lang)
        self._target_combo.setCurrentText(tgt)
        self._temp_spin.setValue(cfg.temperature)
        self._maxlen_spin.setValue(cfg.max_length)

        cc = self._config.clipboard
        self._poll_spin.setValue(cc.poll_interval_ms)
        self._auto_translate_cb.setChecked(cc.auto_translate)
        self._enable_cleaner_cb.setChecked(self._config.clipboard.enable_cleaner)

        cl = self._config.cleaner
        self._fix_hyphen_cb.setChecked(cl.fix_hyphenation)
        self._merge_lines_cb.setChecked(cl.merge_paragraph_lines)
        self._preserve_para_cb.setChecked(cl.preserve_paragraph_breaks)

        oc = self._config.output
        self._auto_copy_cb.setChecked(oc.auto_copy_result)
        self._auto_paste_cb.setChecked(oc.auto_paste)
        self._mode_combo.setCurrentText(oc.show_mode)

    def _save_config(self) -> None:
        """从 UI 保存值到配置。"""
        cfg = self._config.translation
        cfg.active_model = self._model_combo.currentText()
        cfg.source_lang = _LANG_CODE.get(self._source_combo.currentText(), self._source_combo.currentText())
        cfg.target_lang = _LANG_CODE.get(self._target_combo.currentText(), self._target_combo.currentText())
        cfg.temperature = self._temp_spin.value()
        cfg.max_length = self._maxlen_spin.value()

        cc = self._config.clipboard
        cc.poll_interval_ms = self._poll_spin.value()
        cc.auto_translate = self._auto_translate_cb.isChecked()
        cc.enable_cleaner = self._enable_cleaner_cb.isChecked()

        cl = self._config.cleaner
        cl.fix_hyphenation = self._fix_hyphen_cb.isChecked()
        cl.merge_paragraph_lines = self._merge_lines_cb.isChecked()
        cl.preserve_paragraph_breaks = self._preserve_para_cb.isChecked()

        oc = self._config.output
        oc.auto_copy_result = self._auto_copy_cb.isChecked()
        oc.auto_paste = self._auto_paste_cb.isChecked()
        oc.show_mode = self._mode_combo.currentText()

        self._config.save()

    def _on_ok(self) -> None:
        """确认保存配置。"""
        self._save_config()
        self.accept()