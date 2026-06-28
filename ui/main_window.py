"""最小 GUI 主窗口。

使用 tkinter 创建的简易翻译窗口，支持手动输入翻译。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional

from core.pipeline import Pipeline
from core.config import AppConfig


class MainWindow:
    """翻译主窗口。

    包含原文输入框、译文输出框、翻译按钮和配置下拉选择。
    """

    def __init__(
        self,
        pipeline: Optional[Pipeline] = None,
        config: Optional[AppConfig] = None,
    ) -> None:
        self._pipeline = pipeline or Pipeline()
        self._config = config or AppConfig.load()

        self._root = tk.Tk()
        self._root.title("CopyTranslator-Ollama")
        self._root.geometry("700x500")
        self._root.minsize(500, 350)

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

        self._build_ui()

    def _build_ui(self) -> None:
        """构建界面布局。"""
        # --- 顶栏：模型和语言选择 ---
        top_frame = ttk.Frame(self._root, padding="5")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="模型:").pack(side=tk.LEFT)
        model_combo = ttk.Combobox(
            top_frame,
            textvariable=self._model_var,
            values=self._config.models.available,
            width=28,
            state="readonly",
        )
        model_combo.pack(side=tk.LEFT, padx=(2, 10))

        ttk.Label(top_frame, text="源语言:").pack(side=tk.LEFT)
        source_combo = ttk.Combobox(
            top_frame,
            textvariable=self._source_var,
            values=["auto", "en", "zh", "ja", "ko", "fr", "de", "es", "ru"],
            width=8,
            state="readonly",
        )
        source_combo.pack(side=tk.LEFT, padx=(2, 5))

        ttk.Label(top_frame, text="→").pack(side=tk.LEFT, padx=2)

        ttk.Label(top_frame, text="目标语言:").pack(side=tk.LEFT)
        target_combo = ttk.Combobox(
            top_frame,
            textvariable=self._target_var,
            values=["zh", "en", "ja", "ko", "fr", "de", "es", "ru"],
            width=8,
            state="readonly",
        )
        target_combo.pack(side=tk.LEFT, padx=(2, 0))

        # --- 原文区域 ---
        src_frame = ttk.LabelFrame(
            self._root, text="原文", padding="3"
        )
        src_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 2))

        self._src_text = tk.Text(src_frame, wrap=tk.WORD, height=6)
        src_scroll = ttk.Scrollbar(
            src_frame, orient=tk.VERTICAL, command=self._src_text.yview
        )
        self._src_text.configure(yscrollcommand=src_scroll.set)
        self._src_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        src_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 翻译按钮 ---
        btn_frame = ttk.Frame(self._root, padding="3")
        btn_frame.pack(fill=tk.X)

        self._translate_btn = ttk.Button(
            btn_frame,
            text="翻译 (Ctrl+Enter)",
            command=self._do_translate,
        )
        self._translate_btn.pack(side=tk.LEFT, padx=5)

        self._clear_btn = ttk.Button(
            btn_frame,
            text="清空",
            command=self._do_clear,
        )
        self._clear_btn.pack(side=tk.LEFT, padx=5)

        self._status_label = ttk.Label(btn_frame, text="就绪")
        self._status_label.pack(side=tk.RIGHT, padx=5)

        # --- 译文区域 ---
        tgt_frame = ttk.LabelFrame(
            self._root, text="译文", padding="3"
        )
        tgt_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(2, 5))

        self._tgt_text = tk.Text(
            tgt_frame, wrap=tk.WORD, height=8, state=tk.NORMAL
        )
        tgt_scroll = ttk.Scrollbar(
            tgt_frame, orient=tk.VERTICAL, command=self._tgt_text.yview
        )
        self._tgt_text.configure(yscrollcommand=tgt_scroll.set)
        self._tgt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tgt_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # --- 快捷键 ---
        self._root.bind("<Control-Return>", lambda e: self._do_translate())

        # --- 窗口关闭事件 ---
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _do_translate(self) -> None:
        """执行翻译。"""
        text = self._src_text.get("1.0", tk.END).strip()
        if not text:
            self._status_label.configure(text="请输入原文")
            return

        self._status_label.configure(text="翻译中...")
        self._root.update()

        try:
            result = self._pipeline.translate_once(
                text=text,
                source=self._source_var.get(),
                target=self._target_var.get(),
                model=self._model_var.get(),
            )
            self._tgt_text.delete("1.0", tk.END)
            self._tgt_text.insert("1.0", result)
            self._status_label.configure(text="完成")
        except Exception as e:
            self._tgt_text.delete("1.0", tk.END)
            self._tgt_text.insert("1.0", f"翻译失败: {e}")
            self._status_label.configure(text="错误")

    def _do_clear(self) -> None:
        """清空原文和译文。"""
        self._src_text.delete("1.0", tk.END)
        self._tgt_text.delete("1.0", tk.END)
        self._status_label.configure(text="已清空")

    def _on_close(self) -> None:
        """窗口关闭时释放资源。"""
        self._pipeline.close()
        self._root.destroy()

    def run(self) -> None:
        """启动主循环。"""
        self._root.mainloop()
