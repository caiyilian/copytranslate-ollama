"""PyQt6 对照模式主窗口。

左右分栏布局，原文（左）+ 译文（右），支持自动翻译和模型热切换。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from core.config import AppConfig
from core.pipeline import Pipeline
from core.snapshot_manager import SnapshotManager


# 语言代码 -> 中文显示名
_LANG_DISPLAY = {
    "auto": "自动检测",
    "zh": "简体中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "ru": "Русский",
    "ar": "العربية",
    "pt": "Português",
    "it": "Italiano",
    "vi": "Tiếng Việt",
    "th": "ไทย",
}
# 反向映射：显示名 -> 语言代码
_LANG_CODE = {v: k for k, v in _LANG_DISPLAY.items()}


class MainWindow(QMainWindow):
    """对照模式主窗口。"""

    def __init__(
        self,
        pipeline: Optional[Pipeline] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        super().__init__()

        self._pipeline = pipeline or Pipeline()
        self._config = config or AppConfig.load()
        self._snap_manager = SnapshotManager(self._config)
        self._translating = False

        self.setWindowTitle("CopyTranslator-Ollama")
        self.setMinimumSize(600, 350)
        self.resize(900, 550)

        self._build_menus()
        self._build_central()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # 菜单栏
    # ------------------------------------------------------------------

    def _build_menus(self) -> None:
        """构建菜单栏。"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件(&F)")
        exit_action = QAction("退出(&Q)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")
        focus_action = QAction("专注模式(&F)", self)
        focus_action.setEnabled(False)  # Phase 9 实现
        view_menu.addAction(focus_action)

    # ------------------------------------------------------------------
    # 中央区域
    # ------------------------------------------------------------------

    def _build_central(self) -> None:
        """构建中央布局。"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- 顶部工具栏 ---
        self._build_toolbar(layout)

        # --- 左右分栏 ---
        self._build_splitter(layout)

        # --- 底部按钮栏 ---
        self._build_bottom_bar(layout)

    def _build_toolbar(self, parent_layout: QVBoxLayout) -> None:
        """构建顶部工具栏。"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        parent_layout.addWidget(toolbar)

        # 模型选择
        toolbar.addWidget(QLabel("模型:"))
        self._model_combo = QComboBox()
        self._model_combo.addItems(self._config.models.available)
        current = self._config.translation.active_model
        if current in self._config.models.available:
            self._model_combo.setCurrentText(current)
        self._model_combo.setMinimumWidth(180)
        toolbar.addWidget(self._model_combo)
        toolbar.addSeparator()

        # 源语言
        toolbar.addWidget(QLabel("源语言:"))
        self._source_combo = QComboBox()
        self._source_combo.addItems(list(_LANG_DISPLAY.values()))
        source_display = _LANG_DISPLAY.get(
            self._config.translation.source_lang,
            self._config.translation.source_lang,
        )
        self._source_combo.setCurrentText(source_display)
        toolbar.addWidget(self._source_combo)

        # 目标语言
        toolbar.addWidget(QLabel("→"))
        self._target_combo = QComboBox()
        target_values = [v for k, v in _LANG_DISPLAY.items() if k != "auto"]
        self._target_combo.addItems(target_values)
        target_display = _LANG_DISPLAY.get(
            self._config.translation.target_lang,
            self._config.translation.target_lang,
        )
        self._target_combo.setCurrentText(target_display)
        toolbar.addWidget(self._target_combo)
        toolbar.addSeparator()

        # 翻译按钮
        self._translate_btn = QPushButton("翻译")
        self._translate_btn.setShortcut("Ctrl+Return")
        toolbar.addWidget(self._translate_btn)

        # 清空按钮
        self._clear_btn = QPushButton("清空")
        toolbar.addWidget(self._clear_btn)

    def _build_splitter(self, parent_layout: QVBoxLayout) -> None:
        """构建左右分栏。"""
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：原文
        src_frame = QWidget()
        src_layout = QVBoxLayout(src_frame)
        src_layout.setContentsMargins(0, 0, 0, 0)
        src_label = QLabel("原文")
        src_label.setStyleSheet("font-weight: bold; padding: 2px 5px;")
        src_layout.addWidget(src_label)

        self._src_text = QTextEdit()
        self._src_text.setPlaceholderText("在此输入或粘贴原文...")
        src_layout.addWidget(self._src_text)
        self._splitter.addWidget(src_frame)

        # 右侧：译文
        tgt_frame = QWidget()
        tgt_layout = QVBoxLayout(tgt_frame)
        tgt_layout.setContentsMargins(0, 0, 0, 0)
        tgt_label = QLabel("译文")
        tgt_label.setStyleSheet("font-weight: bold; padding: 2px 5px;")
        tgt_layout.addWidget(tgt_label)

        self._tgt_text = QTextEdit()
        self._tgt_text.setReadOnly(True)
        self._tgt_text.setPlaceholderText("译文将显示在此...")
        tgt_layout.addWidget(self._tgt_text)
        self._splitter.addWidget(tgt_frame)

        self._splitter.setSizes([450, 450])
        parent_layout.addWidget(self._splitter, stretch=1)

    def _build_bottom_bar(self, parent_layout: QVBoxLayout) -> None:
        """构建底部按钮栏。"""
        bar = QFrame()
        bar.setFrameShape(QFrame.Shape.StyledPanel)
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(5, 2, 5, 2)

        # 左侧按钮组
        for text, slots in [
            ("历史", None),
            ("统计", None),
            ("导出", None),
            ("日志", None),
            ("关于", None),
        ]:
            btn = QPushButton(text)
            btn.setEnabled(False)  # Phase 12-13 实现
            bar_layout.addWidget(btn)

        bar_layout.addStretch()

        # 右侧按钮
        self._mode_btn = QPushButton("专注模式 >>")
        self._mode_btn.setEnabled(False)  # Phase 9 实现
        bar_layout.addWidget(self._mode_btn)

        parent_layout.addWidget(bar)

    # ------------------------------------------------------------------
    # 状态栏
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        """构建状态栏。"""
        status_bar = self.statusBar()

        # 进度条
        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedWidth(150)
        self._progress.setVisible(False)
        status_bar.addPermanentWidget(self._progress)

        # 状态标签
        self._status_label = QLabel("就绪")
        status_bar.addPermanentWidget(self._status_label)

    # ------------------------------------------------------------------
    # 进度更新
    # ------------------------------------------------------------------

    def _show_progress(self, current: int, total: int) -> None:
        """更新进度条（从工作线程调用，线程安全）。"""
        # 通过信号槽实现（Phase 4 完整实现）
        pass

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore
        """窗口关闭事件。"""
        self._pipeline.close()
        event.accept()