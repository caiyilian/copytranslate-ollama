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

        # 剪贴板监听
        self._clip_watcher = ClipboardWatcher(
            callback=self._on_clipboard_change,
            config=self._config.clipboard,
        )
        self._clip_running = False
        self._clip_paused = False
        self._clip_thread: Optional[threading.Thread] = None
        self._last_clip_hash: Optional[str] = None

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
            result = self._pipeline.translate_once(
                text=text,
                source=self._source_var.get(),
                target=self._target_var.get(),
                model=self._model_var.get(),
            )
            self._set_tgt_text(result)
            char_count = len(result)
            self._status_label.configure(
                text=f"完成 ({char_count} 字符)"
            )
        except Exception as e:
            self._set_tgt_text(f"[翻译失败] {e}")
            self._status_label.configure(text="错误")
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

    def _on_close(self) -> None:
        """窗口关闭时释放资源。"""
        if self._auto_translate_after_id:
            self._root.after_cancel(self._auto_translate_after_id)
        self._stop_clipboard_watch()
        self._pipeline.close()
        self._root.destroy()

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
        else:
            self._clip_paused = True
            self._clip_btn.configure(text="📋 已暂停")
            self._status_label.configure(text="剪贴板监听已暂停")

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
        self._root.mainloop()