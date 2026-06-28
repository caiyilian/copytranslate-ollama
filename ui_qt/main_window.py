"""PyQt6 对照模式主窗口。

左右分栏布局，原文（左）+ 译文（右），支持自动翻译和模型热切换。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QThread
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
from ui_qt.translate_worker import TranslateWorker
from ui_qt.clipboard_worker import ClipboardWatchWorker
from ui_qt.tray import SystemTray
from ui_qt.focus_window import FocusWindow
from ui_qt.settings_dialog import SettingsDialog


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
        self._connect_signals()
        self._start_clipboard_watch()
        self._build_tray()

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
        focus_action.triggered.connect(self._open_focus_mode)
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

        bar_layout.addWidget(QLabel("  "))

        # 设置按钮
        self._settings_btn = QPushButton("设置")
        self._settings_btn.clicked.connect(self._open_settings)
        bar_layout.addWidget(self._settings_btn)

        bar_layout.addStretch()

        # 右侧按钮
        self._mode_btn = QPushButton("专注模式 >>")
        self._mode_btn.clicked.connect(self._open_focus_mode)
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
    # 信号连接
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        """连接信号槽。"""
        self._translate_btn.clicked.connect(self._do_translate)
        self._clear_btn.clicked.connect(self._do_clear)

    # ------------------------------------------------------------------
    # 翻译操作
    # ------------------------------------------------------------------

    def _do_translate(self) -> None:
        """执行翻译（启动工作线程）。"""
        text = self._src_text.toPlainText().strip()
        if not text:
            self._status_label.setText("请输入原文")
            return

        if self._translating:
            return

        self._translating = True
        self._translate_btn.setEnabled(False)
        self._status_label.setText("翻译中...")
        self._progress.setVisible(True)
        self._progress.setValue(0)

        source_display = self._source_combo.currentText()
        target_display = self._target_combo.currentText()
        source_code = _LANG_CODE.get(source_display, source_display)
        target_code = _LANG_CODE.get(target_display, target_display)

        # 创建工作线程
        self._thread = QThread()
        self._worker = TranslateWorker(self._pipeline)
        self._worker.moveToThread(self._thread)

        # 连接信号
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_translation_done)
        self._worker.error_occurred.connect(self._on_translation_error)
        self._thread.started.connect(
            lambda: self._worker.run(
                text=text,
                source=source_code,
                target=target_code,
                model=self._model_combo.currentText(),
            )
        )
        self._worker.finished.connect(self._thread.quit)
        self._worker.error_occurred.connect(self._thread.quit)
        self._thread.finished.connect(self._cleanup_thread)

        self._thread.start()

    def _on_progress(self, current: int, total: int) -> None:
        """进度更新（主线程）。"""
        pct = int(current / total * 100)
        self._progress.setValue(pct)
        self._progress.setFormat(f"{current}/{total}")
        self._status_label.setText(f"翻译中: {current}/{total} 段")

    def _on_translation_done(self, result: str, detected: str) -> None:
        """翻译完成（主线程）。"""
        self._tgt_text.setText(result)
        self._progress.setValue(100)
        self._progress.setFormat("完成")
        lang_label = _LANG_DISPLAY.get(detected, detected) if detected else ""
        suffix = f"  [{lang_label}]" if lang_label else ""
        self._status_label.setText(
            f"完成 ({len(result)} 字符){suffix}"
        )

    def _on_translation_error(self, message: str) -> None:
        """翻译失败（主线程）。"""
        self._tgt_text.setText(f"[翻译失败] {message}")
        self._status_label.setText("错误")
        self._progress.setVisible(False)

    def _cleanup_thread(self) -> None:
        """清理工作线程。"""
        self._translating = False
        self._translate_btn.setEnabled(True)
        if hasattr(self, "_thread"):
            self._thread.deleteLater()
            del self._thread
        if hasattr(self, "_worker"):
            self._worker.deleteLater()
            del self._worker

    def _do_clear(self) -> None:
        """清空原文和译文。"""
        self._src_text.clear()
        self._tgt_text.clear()
        self._status_label.setText("已清空")
        self._progress.setVisible(False)
        self._progress.setValue(0)
        self._translating = False
        self._translate_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # 进度更新
    # ------------------------------------------------------------------

    def _show_progress(self, current: int, total: int) -> None:
        """更新进度条（从工作线程调用，线程安全）。"""
        # 通过信号槽实现（Phase 4 完整实现）
        pass

    # ------------------------------------------------------------------
    # 剪贴板监听
    # ------------------------------------------------------------------

    def _start_clipboard_watch(self) -> None:
        """启动后台剪贴板监听线程。"""
        self._clip_thread = QThread()
        self._clip_worker = ClipboardWatchWorker()
        self._clip_worker.moveToThread(self._clip_thread)
        self._clip_worker.clipboard_changed.connect(self._on_clipboard_change)
        self._clip_thread.started.connect(self._clip_worker.run)
        self._clip_thread.start()

    def _stop_clipboard_watch(self) -> None:
        """停止剪贴板监听。"""
        if hasattr(self, "_clip_worker"):
            self._clip_worker.stop()
            self._clip_worker.deleteLater()
        if hasattr(self, "_clip_thread"):
            self._clip_thread.quit()
            self._clip_thread.wait(2000)
            self._clip_thread.deleteLater()

    def _on_clipboard_change(self, text: str) -> None:
        """剪贴板内容变化（主线程）。"""
        self._src_text.setText(text)
        self._status_label.setText(f"检测到剪贴板 ({len(text)} 字符)")
        self._do_translate()

    # ------------------------------------------------------------------
    # 系统托盘
    # ------------------------------------------------------------------

    def _build_tray(self) -> None:
        """构建系统托盘。"""
        self._tray = SystemTray(
            tooltip="CopyTranslator-Ollama",
            on_show=self._toggle_visible,
            on_focus=self._open_focus_mode,
            on_toggle_pause=self._toggle_clipboard_pause,
            on_switch_model=self._cycle_model,
            on_quit=self._quit_app,
        )
        self._tray.show()

    def _toggle_visible(self) -> None:
        """切换窗口显示/隐藏。"""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def _toggle_clipboard_pause(self) -> None:
        """切换剪贴板监听暂停/恢复。"""
        if hasattr(self, "_clip_worker"):
            if self._clip_worker.is_paused:
                self._clip_worker.resume()
                self._tray.set_pause_text(False)
                self._status_label.setText("剪贴板监听已恢复")
            else:
                self._clip_worker.pause()
                self._tray.set_pause_text(True)
                self._status_label.setText("剪贴板监听已暂停")

    def _cycle_model(self) -> None:
        """切换下一个可用模型。"""
        models = self._config.models.available
        current = self._model_combo.currentText()
        if current in models:
            idx = (models.index(current) + 1) % len(models)
            self._model_combo.setCurrentText(models[idx])
            self._status_label.setText(f"已切换: {models[idx]}")

    def _open_focus_mode(self) -> None:
        """打开专注模式浮窗。"""
        self._focus_window = FocusWindow(
            pipeline=self._pipeline,
            config=self._config,
            main_window=self,
        )
        self._focus_window.show()
        self.hide()

    def _quit_app(self) -> None:
        """彻底退出程序。"""
        self._stop_clipboard_watch()
        self._pipeline.close()
        if hasattr(self, "_tray"):
            self._tray.hide()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    def _open_settings(self) -> None:
        """打开设置面板。"""
        dialog = SettingsDialog(
            parent=self,
            config=self._config,
        )
        if dialog.exec():
            self._status_label.setText("设置已保存")
            # 刷新模型下拉
            self._model_combo.clear()
            self._model_combo.addItems(self._config.models.available)
            self._model_combo.setCurrentText(self._config.translation.active_model)
            # 刷新语言
            self._source_combo.setCurrentText(
                _LANG_DISPLAY.get(self._config.translation.source_lang, self._config.translation.source_lang)
            )
            self._target_combo.setCurrentText(
                _LANG_DISPLAY.get(self._config.translation.target_lang, self._config.translation.target_lang)
            )

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:  # type: ignore
        """窗口关闭 → 隐藏到托盘（不退出）。"""
        self.hide()
        event.ignore()