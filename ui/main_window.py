"""对照模式主窗口。

左右分栏布局，原文（左）+ 译文（右），支持自动翻译和模型热切换。
集成后台剪贴板监听，复制文本自动填充原文并翻译。
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.clipboard import ClipboardWatcher
from core.pipeline import Pipeline
from core.config import AppConfig
from core.snapshot_manager import SnapshotManager
from core.startup import is_enabled as is_startup_enabled
from core.startup import toggle as toggle_startup
from ui.tray import SystemTray


# 自动翻译延迟（毫秒）：用户停止输入后再触发翻译
_AUTO_TRANSLATE_DELAY_MS = 600
# 剪贴板轮询间隔（毫秒）
_CLIPBOARD_POLL_MS = 500


class MainWindow:
    """对照模式主窗口。

    左右 PanedWindow 分栏，左侧可编辑原文，右侧只读译文。
    支持自动翻译（输入延迟后触发）、模型/语言热切换和后台剪贴板监听。
    """

    def __init__(
        self,
        pipeline: Optional[Pipeline] = None,
        config: Optional[AppConfig] = None,
        mode: str = "contrast",
    ) -> None:
        self._pipeline = pipeline or Pipeline()
        self._config = config or AppConfig.load()

        self._root = tk.Tk()
        mode_title = "对照模式" if mode == "contrast" else "专注模式"
        self._root.title(f"CopyTranslator-Ollama — {mode_title}")
        self._root.geometry("900x550")
        self._root.minsize(600, 350)

        # 状态变量
        self._source_var = tk.StringVar(
            value=self._config.translation.source_lang
        )
        self._target_var = tk.StringVar(
            value=self._config.translation.target_lang
        )
        self._model_var = tk.StringVar(
            value=self._config.translation.active_model
        )
        self._auto_translate_var = tk.BooleanVar(value=True)

        # 自动翻译定时器 ID
        self._auto_translate_after_id: Optional[str] = None

        # 当前翻译中的标记
        self._translating = False

        # 语言代码 → 名称映射（用于自动检测结果显示）
        self._lang_names = {
            "en": "English", "zh": "中文", "ja": "日本語",
            "ko": "한국어", "fr": "Français", "de": "Deutsch",
            "es": "Español", "ru": "Русский", "ar": "العربية",
            "pt": "Português", "th": "ไทย",
        }

        # 快照管理器
        self._snap_manager = SnapshotManager(self._config)

        # 剪贴板监听
        self._clip_watcher = ClipboardWatcher(
            callback=self._on_clipboard_change,
            config=self._config.clipboard,
        )
        self._clip_running = False
        self._clip_paused = False
        self._clip_thread: Optional[threading.Thread] = None
        self._last_clip_hash: Optional[str] = None

        # 系统托盘
        self._tray = SystemTray(
            tooltip="CopyTranslator-Ollama",
            on_show=self._show_window,
            on_focus=self._open_focus_mode,
            on_toggle_pause=self._toggle_clipboard,
            on_switch_model=self._cycle_model,
            on_quit=self._quit_app,
        )

        self._build_ui()
        self._bind_events()

    def _build_ui(self) -> None:
        """构建界面布局。"""
        # --- 顶栏：模型和语言选择 ---
        top_frame = ttk.Frame(self._root, padding="5")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="模型:").pack(side=tk.LEFT)
        self._model_combo = ttk.Combobox(
            top_frame,
            textvariable=self._model_var,
            values=self._config.models.available,
            width=28,
            state="readonly",
        )
        self._model_combo.pack(side=tk.LEFT, padx=(2, 10))

        ttk.Label(top_frame, text="源语言:").pack(side=tk.LEFT)
        self._source_combo = ttk.Combobox(
            top_frame,
            textvariable=self._source_var,
            values=[
                "auto", "en", "zh", "ja", "ko",
                "fr", "de", "es", "ru", "ar", "pt", "it", "vi", "th",
            ],
            width=8,
            state="readonly",
        )
        self._source_combo.pack(side=tk.LEFT, padx=(2, 5))

        ttk.Label(top_frame, text="→").pack(side=tk.LEFT, padx=2)

        ttk.Label(top_frame, text="目标语言:").pack(side=tk.LEFT)
        self._target_combo = ttk.Combobox(
            top_frame,
            textvariable=self._target_var,
            values=[
                "zh", "en", "ja", "ko", "fr", "de",
                "es", "ru", "ar", "pt", "it", "vi", "th",
            ],
            width=8,
            state="readonly",
        )
        self._target_combo.pack(side=tk.LEFT, padx=(2, 5))

        # 自动翻译开关
        self._auto_cb = ttk.Checkbutton(
            top_frame,
            text="自动",
            variable=self._auto_translate_var,
        )
        self._auto_cb.pack(side=tk.LEFT, padx=(10, 0))

        # 剪贴板监听按钮
        self._clip_btn = ttk.Button(
            top_frame,
            text="📋 监听中",
            command=self._toggle_clipboard,
            width=10,
        )
        self._clip_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 快照选择
        ttk.Label(top_frame, text="快照:").pack(side=tk.LEFT, padx=(10, 2))
        self._snap_var = tk.StringVar()
        self._snap_combo = ttk.Combobox(
            top_frame,
            textvariable=self._snap_var,
            values=self._snap_manager.snapshot_names(),
            width=14,
            state="readonly",
        )
        self._snap_combo.pack(side=tk.LEFT, padx=(0, 2))
        self._snap_combo.bind("<<ComboboxSelected>>", self._on_snapshot_selected)

        ttk.Button(
            top_frame, text="管理", width=5, command=self._open_snapshots
        ).pack(side=tk.LEFT, padx=(0, 5))

        # 开机自启开关
        self._startup_var = tk.BooleanVar(value=is_startup_enabled())
        self._startup_cb = ttk.Checkbutton(
            top_frame,
            text="自启",
            variable=self._startup_var,
            command=self._toggle_startup,
        )
        self._startup_cb.pack(side=tk.LEFT, padx=(10, 0))

        # 状态栏（右侧）
        self._status_label = ttk.Label(top_frame, text="就绪")
        self._status_label.pack(side=tk.RIGHT, padx=5)

        # --- 左右分栏：原文 | 译文 ---
        self._paned = ttk.PanedWindow(
            self._root, orient=tk.HORIZONTAL
        )
        self._paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧：原文
        src_frame = ttk.LabelFrame(
            self._paned, text="原文", padding="3"
        )
        self._src_text = tk.Text(src_frame, wrap=tk.WORD, padx=5, pady=5)
        src_scroll = ttk.Scrollbar(
            src_frame, orient=tk.VERTICAL, command=self._src_text.yview
        )
        self._src_text.configure(yscrollcommand=src_scroll.set)
        self._src_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        src_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._paned.add(src_frame, weight=1)

        # 右侧：译文
        tgt_frame = ttk.LabelFrame(
            self._paned, text="译文", padding="3"
        )
        self._tgt_text = tk.Text(
            tgt_frame, wrap=tk.WORD, padx=5, pady=5,
            state=tk.DISABLED,
        )
        tgt_scroll = ttk.Scrollbar(
            tgt_frame, orient=tk.VERTICAL, command=self._tgt_text.yview
        )
        self._tgt_text.configure(yscrollcommand=tgt_scroll.set)
        self._tgt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tgt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._paned.add(tgt_frame, weight=1)

        # --- 底栏：操作按钮 ---
        bottom_frame = ttk.Frame(self._root, padding="3")
        bottom_frame.pack(fill=tk.X)

        self._translate_btn = ttk.Button(
            bottom_frame,
            text="翻译 (Ctrl+Enter)",
            command=self._do_translate,
        )
        self._translate_btn.pack(side=tk.LEFT, padx=5)

        self._clear_btn = ttk.Button(
            bottom_frame,
            text="清空",
            command=self._do_clear,
        )
        self._clear_btn.pack(side=tk.LEFT, padx=5)

        # 历史按钮
        self._history_btn = ttk.Button(
            bottom_frame,
            text="历史",
            command=self._open_history,
        )
        self._history_btn.pack(side=tk.LEFT, padx=5)

        # 统计按钮
        self._stats_btn = ttk.Button(
            bottom_frame,
            text="统计",
            command=self._open_stats,
        )
        self._stats_btn.pack(side=tk.LEFT, padx=5)

        # 日志按钮
        self._log_btn = ttk.Button(
            bottom_frame,
            text="日志",
            command=self._open_logs,
        )
        self._log_btn.pack(side=tk.LEFT, padx=5)

        # 导出按钮
        self._export_btn = ttk.Button(
            bottom_frame,
            text="导出",
            command=self._open_export,
        )
        self._export_btn.pack(side=tk.LEFT, padx=5)

        # 关于按钮
        self._about_btn = ttk.Button(
            bottom_frame,
            text="关于",
            command=self._open_about,
        )
        self._about_btn.pack(side=tk.LEFT, padx=5)

        # 设置按钮
        self._settings_btn = ttk.Button(
            bottom_frame,
            text="设置",
            command=self._open_settings,
        )
        self._settings_btn.pack(side=tk.LEFT, padx=5)

        # 模式切换按钮
        self._mode_btn = ttk.Button(
            bottom_frame,
            text="专注模式 >>",
            command=self._switch_to_focus,
        )
        self._mode_btn.pack(side=tk.RIGHT, padx=5)

    def _bind_events(self) -> None:
        """绑定事件。"""
        # 原文变化 -> 自动翻译
        self._src_text.bind(
            "<KeyRelease>", self._on_source_change
        )

        # 快捷键
        self._root.bind(
            "<Control-Return>",
            lambda e: self._do_translate(),
        )
        self._root.bind(
            "<Control-l>",
            lambda e: self._do_clear(),
        )
        self._root.bind(
            "<Control-h>",
            lambda e: self._open_history(),
        )
        self._root.bind(
            "<Control-l>",
            lambda e: self._do_clear(),
        )
        self._root.bind(
            "<Control-k>",
            lambda e: self._open_logs(),
        )

        # 模型/语言切换 -> 重新翻译
        self._model_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._schedule_translate(),
        )
        self._source_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._schedule_translate(),
        )
        self._target_combo.bind(
            "<<ComboboxSelected>>",
            lambda e: self._schedule_translate(),
        )

        # 窗口关闭
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_source_change(self, event: tk.Event) -> None:
        """原文变化事件处理。"""
        if self._auto_translate_var.get():
            self._schedule_translate()

    def _schedule_translate(self) -> None:
        """安排延迟翻译。"""
        if self._auto_translate_after_id:
            self._root.after_cancel(self._auto_translate_after_id)
        self._auto_translate_after_id = self._root.after(
            _AUTO_TRANSLATE_DELAY_MS, self._do_translate
        )

    def _set_tgt_text(self, text: str) -> None:
        """设置译文文本（线程安全，在主线程调用）。"""
        self._tgt_text.configure(state=tk.NORMAL)
        self._tgt_text.delete("1.0", tk.END)
        self._tgt_text.insert("1.0", text)
        self._tgt_text.configure(state=tk.DISABLED)

    def _do_translate(self) -> None:
        """执行翻译。"""
        text = self._src_text.get("1.0", tk.END).strip()
        if not text:
            self._status_label.configure(text="请输入原文")
            return

        if self._translating:
            return  # 防止重复触发

        self._translating = True
        self._status_label.configure(text="翻译中...")
        self._root.update()

        try:
            result, detected = self._pipeline.translate_once(
                text=text,
                source=self._source_var.get(),
                target=self._target_var.get(),
                model=self._model_var.get(),
            )
            self._set_tgt_text(result)
            lang_label = self._lang_names.get(detected, detected)
            self._status_label.configure(
                text=f"完成 ({len(result)} 字符)  [{lang_label}]"
            )
        except Exception as e:
            self._set_tgt_text(f"[翻译失败] {e}")
            self._status_label.configure(text="错误")
            from ui.toast import Toast
            Toast.error(self._root, f"翻译失败: {e}")
        finally:
            self._translating = False

    def _do_clear(self) -> None:
        """清空原文和译文。"""
        if self._auto_translate_after_id:
            self._root.after_cancel(self._auto_translate_after_id)
            self._auto_translate_after_id = None
        self._src_text.delete("1.0", tk.END)
        self._set_tgt_text("")
        self._status_label.configure(text="已清空")
        from ui.toast import Toast
        Toast.info(self._root, "已清空")

    def _on_close(self) -> None:
        """窗口关闭时最小化到托盘。"""
        if self._auto_translate_after_id:
            self._root.after_cancel(self._auto_translate_after_id)
        self._root.withdraw()
        self._tray.set_status(
            paused=self._clip_paused, visible=False
        )

    def _show_window(self) -> None:
        """从托盘显示窗口。"""
        self._root.deiconify()
        self._root.lift()
        self._tray.set_status(
            paused=self._clip_paused, visible=True
        )

    def _open_focus_mode(self) -> None:
        """从托盘打开专注模式窗口。"""
        self._switch_to_focus()

    def _switch_to_focus(self) -> None:
        """切换到专注模式。"""
        from ui.focus_window import FocusWindow

        # 隐藏对照窗口
        self._root.withdraw()
        self._tray.set_status(
            paused=self._clip_paused, visible=False
        )

        # 打开专注窗口（共享 pipeline）
        fw = FocusWindow(
            pipeline=self._pipeline,
            config=self._config,
            main_window=self,
        )
        fw.run()

    def _open_settings(self) -> None:
        """打开设置面板。"""
        from ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog(
            parent=self._root,
            config=self._config,
            on_save=self._on_settings_saved,
        )
        dialog.wait()

    def _on_settings_saved(self, config: AppConfig) -> None:
        """设置保存后的回调。"""
        # 更新 UI 中的模型/语言选择
        self._model_var.set(config.translation.active_model)
        self._source_var.set(config.translation.source_lang)
        self._target_var.set(config.translation.target_lang)
        self._status_label.configure(text="设置已保存")
        from ui.toast import Toast
        Toast.success(self._root, "设置已保存")

        # 如果当前有原文，重新翻译
        text = self._src_text.get("1.0", tk.END).strip()
        if text:
            self._schedule_translate()

    def _on_snapshot_selected(self, event: object = None) -> None:
        """快照下拉框选择后的回调。"""
        name = self._snap_var.get()
        if not name:
            return
        success = self._snap_manager.apply_snapshot(name, self._config)
        if success:
            self._config.save()
            # 更新 UI 控件状态
            self._model_var.set(self._config.translation.active_model)
            self._source_var.set(self._config.translation.source_lang)
            self._target_var.set(self._config.translation.target_lang)
            self._status_label.configure(text=f"已加载快照: {name}")
            from ui.toast import Toast
            Toast.info(self._root, f"已加载快照: {name}")
            # 如果有原文，重新翻译
            text = self._src_text.get("1.0", tk.END).strip()
            if text:
                self._schedule_translate()

    def _open_snapshots(self) -> None:
        """打开快照管理对话框。"""
        from ui.snapshot_dialog import SnapshotDialog

        def on_select(name: str) -> None:
            """快照加载后的回调。"""
            self._config.save()
            self._model_var.set(self._config.translation.active_model)
            self._source_var.set(self._config.translation.source_lang)
            self._target_var.set(self._config.translation.target_lang)
            # 刷新快照列表
            self._snap_combo.configure(
                values=self._snap_manager.snapshot_names()
            )
            self._snap_var.set(name)
            self._status_label.configure(text=f"已加载快照: {name}")
            text = self._src_text.get("1.0", tk.END).strip()
            if text:
                self._schedule_translate()

        dialog = SnapshotDialog(
            parent=self._root,
            config=self._config,
            on_select=on_select,
        )
        dialog.wait()
        # 对话框关闭后刷新列表
        self._snap_combo.configure(
            values=self._snap_manager.snapshot_names()
        )

    def _cycle_model(self) -> None:
        """切换下一个可用模型。"""
        models = self._config.models.available
        current = self._model_var.get()
        if current in models:
            idx = (models.index(current) + 1) % len(models)
            self._model_var.set(models[idx])
            self._status_label.configure(
                text=f"已切换: {models[idx]}"
            )
            self._schedule_translate()

    def _quit_app(self) -> None:
        """彻底退出程序。"""
        self._tray.destroy()
        if self._auto_translate_after_id:
            self._root.after_cancel(self._auto_translate_after_id)
        self._stop_clipboard_watch()
        self._pipeline.close()
        self._root.quit()
        self._root.destroy()

    # ------------------------------------------------------------------
    # 开机自启
    # ------------------------------------------------------------------

    def _toggle_startup(self) -> None:
        """切换开机自启状态。"""
        new_state = toggle_startup()
        self._startup_var.set(new_state)
        from ui.toast import Toast
        if new_state:
            Toast.success(self._root, "开机自启已启用")
        else:
            Toast.info(self._root, "开机自启已关闭")

    # ------------------------------------------------------------------
    # 历史记录
    # ------------------------------------------------------------------

    def _open_history(self) -> None:
        """打开翻译历史对话框。"""
        from ui.history_dialog import HistoryDialog

        dialog = HistoryDialog(parent=self._root)
        dialog.wait()

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def _open_stats(self) -> None:
        """打开翻译统计面板。"""
        from ui.stats_dialog import StatsDialog

        dialog = StatsDialog(parent=self._root)
        dialog.wait()

    # ------------------------------------------------------------------
    # 日志
    # ------------------------------------------------------------------

    def _open_logs(self) -> None:
        """打开日志查看对话框。"""
        from ui.log_dialog import LogDialog

        dialog = LogDialog(parent=self._root)
        dialog.wait()

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------

    def _open_export(self) -> None:
        """打开翻译导出对话框。"""
        from ui.export_dialog import ExportDialog

        dialog = ExportDialog(parent=self._root)
        dialog.wait()

    # ------------------------------------------------------------------
    # 关于
    # ------------------------------------------------------------------

    def _open_about(self) -> None:
        """打开关于对话框。"""
        from ui.about_dialog import AboutDialog

        dialog = AboutDialog(parent=self._root)
        dialog.wait()

    # ------------------------------------------------------------------
    # 剪贴板监听
    # ------------------------------------------------------------------

    def _on_clipboard_change(self, text: str) -> None:
        """剪贴板变化回调（在监听线程中调用）。"""
        if self._clip_paused:
            return

        # 通过 after() 在主线程更新 UI
        self._root.after(0, self._handle_clipboard_text, text)

    def _handle_clipboard_text(self, text: str) -> None:
        """在主线程中处理剪贴板文本。"""
        # 清空原文、填入新内容
        self._src_text.delete("1.0", tk.END)
        self._src_text.insert("1.0", text)

        self._status_label.configure(
            text=f"检测到剪贴板 ({len(text)} 字符)"
        )

        # 自动翻译
        if self._auto_translate_var.get():
            self._schedule_translate()

    def _toggle_clipboard(self) -> None:
        """切换剪贴板监听状态。"""
        if self._clip_paused:
            self._clip_paused = False
            self._clip_btn.configure(text="📋 监听中")
            self._status_label.configure(text="剪贴板监听已恢复")
            from ui.toast import Toast
            Toast.info(self._root, "剪贴板监听已恢复")
        else:
            self._clip_paused = True
            self._clip_btn.configure(text="📋 已暂停")
            self._status_label.configure(text="剪贴板监听已暂停")
            from ui.toast import Toast
            Toast.info(self._root, "剪贴板监听已暂停")

    def _clipboard_loop(self) -> None:
        """后台剪贴板轮询循环。"""
        self._clip_running = True
        while self._clip_running:
            try:
                text = self._clip_watcher.poll_once()
                if text is not None:
                    self._on_clipboard_change(text)
            except Exception:
                pass
            import time
            time.sleep(_CLIPBOARD_POLL_MS / 1000.0)

    def _start_clipboard_watch(self) -> None:
        """启动后台剪贴板监听线程。"""
        if self._clip_thread and self._clip_thread.is_alive():
            return
        self._clip_paused = False
        self._clip_thread = threading.Thread(
            target=self._clipboard_loop,
            daemon=True,
            name="clipboard-watcher",
        )
        self._clip_thread.start()
        self._clip_btn.configure(text="📋 监听中")

    def _stop_clipboard_watch(self) -> None:
        """停止后台剪贴板监听。"""
        self._clip_running = False
        self._clip_paused = True
        self._clip_thread = None

    def run(self) -> None:
        """启动主循环。"""
        self._start_clipboard_watch()
        self._tray.create()
        self._root.mainloop()