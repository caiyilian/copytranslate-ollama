"""设置面板 Dialog。

按分类 Tab 组织所有配置项，支持即时修改和持久化保存。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional

from core.config import AppConfig
from core.config_io import export_config, import_config, merge_config


class SettingsDialog:
    """设置面板对话框。

    使用 ttk.Notebook 多 Tab 布局，包含翻译/剪贴板/净化/输出/快捷键设置。
    """

    def __init__(
        self,
        parent: tk.Tk,
        config: AppConfig,
        on_save: Optional[Callable[[AppConfig], None]] = None,
    ) -> None:
        self._config = config
        self._on_save = on_save
        self._callbacks: Dict[str, List[Callable[[], None]]] = {}

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("设置")
        self._dialog.geometry("520x420")
        self._dialog.minsize(480, 350)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()

        # 居中显示
        self._dialog.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        dw = self._dialog.winfo_width()
        dh = self._dialog.winfo_height()
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        self._dialog.geometry(f"+{x}+{y}")

    def _build_ui(self) -> None:
        """构建界面。"""
        notebook = ttk.Notebook(self._dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 各 Tab
        self._build_translation_tab(notebook)
        self._build_clipboard_tab(notebook)
        self._build_cleaner_tab(notebook)
        self._build_output_tab(notebook)
        self._build_hotkey_tab(notebook)

        # 底部按钮
        btn_frame = ttk.Frame(self._dialog, padding="5")
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="保存", command=self._do_save
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            btn_frame, text="取消", command=self._dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            btn_frame, text="导出配置", command=self._do_export
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame, text="导入配置", command=self._do_import
        ).pack(side=tk.LEFT, padx=5)

    def _make_spinbox(
        self,
        parent: tk.Widget,
        label: str,
        from_: int,
        to: int,
        default: int,
    ) -> tk.IntVar:
        """创建带标签的数值输入框。"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        var = tk.IntVar(value=default)
        spin = ttk.Spinbox(
            frame,
            from_=from_,
            to=to,
            textvariable=var,
            width=10,
        )
        spin.pack(side=tk.RIGHT)
        return var

    def _make_checkbox(
        self,
        parent: tk.Widget,
        label: str,
        default: bool,
    ) -> tk.BooleanVar:
        """创建复选框。"""
        var = tk.BooleanVar(value=default)
        cb = ttk.Checkbutton(parent, text=label, variable=var)
        cb.pack(anchor=tk.W, pady=2)
        return var

    def _make_combobox(
        self,
        parent: tk.Widget,
        label: str,
        values: List[str],
        default: str,
        width: int = 15,
    ) -> tk.StringVar:
        """创建下拉选择框。"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
        ttk.Label(frame, text=label, width=20).pack(side=tk.LEFT)
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(
            frame,
            textvariable=var,
            values=values,
            width=width,
            state="readonly",
        )
        combo.pack(side=tk.RIGHT)
        return var

    # ------------------------------------------------------------------
    # Tab 1: 翻译设置
    # ------------------------------------------------------------------

    def _build_translation_tab(self, notebook: ttk.Notebook) -> None:
        """翻译设置 Tab。"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="翻译")

        cfg = self._config.translation

        self._model_var = self._make_combobox(
            frame,
            "模型",
            self._config.models.available,
            cfg.active_model,
            width=28,
        )
        self._source_var = self._make_combobox(
            frame,
            "源语言",
            ["auto", "en", "zh", "ja", "ko", "fr", "de", "es", "ru"],
            cfg.source_lang,
        )
        self._target_var = self._make_combobox(
            frame,
            "目标语言",
            ["zh", "en", "ja", "ko", "fr", "de", "es", "ru"],
            cfg.target_lang,
        )
        self._temp_var = tk.DoubleVar(value=cfg.temperature)
        temp_frame = ttk.Frame(frame)
        temp_frame.pack(fill=tk.X, pady=2)
        ttk.Label(temp_frame, text="温度", width=20).pack(side=tk.LEFT)
        temp_scale = ttk.Scale(
            temp_frame,
            from_=0.0,
            to=2.0,
            variable=self._temp_var,
            orient=tk.HORIZONTAL,
            length=150,
        )
        temp_scale.pack(side=tk.LEFT, padx=5)
        self._temp_label = ttk.Label(temp_frame, text=f"{cfg.temperature:.1f}")
        self._temp_label.pack(side=tk.LEFT)
        temp_scale.configure(
            command=lambda v: self._temp_label.configure(text=f"{float(v):.1f}")
        )

        self._maxlen_var = self._make_spinbox(
            frame, "最大长度", 64, 8192, cfg.max_length
        )

    # ------------------------------------------------------------------
    # Tab 2: 剪贴板设置
    # ------------------------------------------------------------------

    def _build_clipboard_tab(self, notebook: ttk.Notebook) -> None:
        """剪贴板设置 Tab。"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="剪贴板")

        cfg = self._config.clipboard

        self._poll_var = self._make_spinbox(
            frame, "轮询间隔 (ms)", 50, 5000, cfg.poll_interval_ms
        )
        self._auto_translate_var = self._make_checkbox(
            frame, "自动翻译", cfg.auto_translate
        )
        self._enable_cleaner_var = self._make_checkbox(
            frame, "启用文本净化", cfg.enable_cleaner
        )

    # ------------------------------------------------------------------
    # Tab 3: 文本净化设置
    # ------------------------------------------------------------------

    def _build_cleaner_tab(self, notebook: ttk.Notebook) -> None:
        """文本净化设置 Tab。"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="净化")

        cfg = self._config.cleaner

        self._fix_hyphen_var = self._make_checkbox(
            frame, "修复连字符断词 (transla-\\ntion -> translation)",
            cfg.fix_hyphenation,
        )
        self._merge_lines_var = self._make_checkbox(
            frame, "合并段落内换行",
            cfg.merge_paragraph_lines,
        )
        self._preserve_para_var = self._make_checkbox(
            frame, "保留段落之间的空行分隔",
            cfg.preserve_paragraph_breaks,
        )

        ttk.Label(
            frame,
            text="\n文本净化仅在启用剪贴板监听时生效。\n"
                 "修改后对后续复制的内容生效。",
            foreground="#888888",
            wraplength=400,
        ).pack(anchor=tk.W, pady=(20, 0))

    # ------------------------------------------------------------------
    # Tab 4: 输出设置
    # ------------------------------------------------------------------

    def _build_output_tab(self, notebook: ttk.Notebook) -> None:
        """输出设置 Tab。"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="输出")

        cfg = self._config.output

        self._auto_copy_var = self._make_checkbox(
            frame, "翻译完成后自动复制译文到剪贴板",
            cfg.auto_copy_result,
        )
        self._auto_paste_var = self._make_checkbox(
            frame, "自动粘贴替换选中文本（需开启自动复制）",
            cfg.auto_paste,
        )
        self._show_mode_var = self._make_combobox(
            frame,
            "默认显示模式",
            ["contrast", "focus"],
            cfg.show_mode,
        )

    # ------------------------------------------------------------------
    # Tab 5: 快捷键
    # ------------------------------------------------------------------

    def _build_hotkey_tab(self, notebook: ttk.Notebook) -> None:
        """快捷键查看 Tab。"""
        frame = ttk.Frame(notebook, padding="10")
        notebook.add(frame, text="快捷键")

        cfg = self._config.hotkeys

        hotkeys: List[tuple[str, str]] = [
            ("切换窗口显示/隐藏", cfg.toggle_window),
            ("切换翻译模型", cfg.switch_model),
            ("切换对照/专注模式", cfg.toggle_mode),
            ("手动触发翻译", cfg.manual_translate),
            ("清空原文和译文", "Ctrl+L"),
            ("字体放大", "Ctrl+滚轮向上"),
            ("字体缩小", "Ctrl+滚轮向下"),
        ]

        # 表格标题
        header = ttk.Frame(frame)
        header.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(header, text="功能", width=30, font=("", 10, "bold")).pack(
            side=tk.LEFT
        )
        ttk.Label(header, text="快捷键", font=("", 10, "bold")).pack(
            side=tk.LEFT, padx=(20, 0)
        )

        # 分隔线
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(
            fill=tk.X, pady=2
        )

        # 快捷键列表
        for action, key in hotkeys:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=action, width=30).pack(side=tk.LEFT)
            ttk.Label(
                row,
                text=key,
                foreground="#3366cc",
                font=("Consolas", 10),
            ).pack(side=tk.LEFT, padx=(20, 0))

        ttk.Label(
            frame,
            text="\n快捷键编辑将在后续版本中支持。",
            foreground="#888888",
        ).pack(anchor=tk.W, pady=(20, 0))

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------

    def _do_save(self) -> None:
        """保存设置并关闭。"""
        # 翻译
        self._config.translation.active_model = self._model_var.get()
        self._config.translation.source_lang = self._source_var.get()
        self._config.translation.target_lang = self._target_var.get()
        self._config.translation.temperature = round(
            self._temp_var.get(), 1
        )
        self._config.translation.max_length = self._maxlen_var.get()

        # 剪贴板
        self._config.clipboard.poll_interval_ms = self._poll_var.get()
        self._config.clipboard.auto_translate = (
            self._auto_translate_var.get()
        )
        self._config.clipboard.enable_cleaner = (
            self._enable_cleaner_var.get()
        )

        # 净化
        self._config.cleaner.fix_hyphenation = (
            self._fix_hyphen_var.get()
        )
        self._config.cleaner.merge_paragraph_lines = (
            self._merge_lines_var.get()
        )
        self._config.cleaner.preserve_paragraph_breaks = (
            self._preserve_para_var.get()
        )

        # 输出
        self._config.output.auto_copy_result = (
            self._auto_copy_var.get()
        )
        self._config.output.auto_paste = self._auto_paste_var.get()
        self._config.output.show_mode = self._show_mode_var.get()

        # 持久化
        self._config.save()

        # 通知父窗口
        if self._on_save:
            self._on_save(self._config)

        self._dialog.destroy()

    # ------------------------------------------------------------------
    # 导入 / 导出
    # ------------------------------------------------------------------

    def _do_export(self) -> None:
        """导出当前配置到 JSON 文件。"""
        from pathlib import Path
        from tkinter import filedialog

        file_path = filedialog.asksaveasfilename(
            parent=self._dialog,
            title="导出配置",
            defaultextension=".json",
            filetypes=[("JSON 配置文件", "*.json")],
            initialfile="copytranslate-config.json",
        )
        if not file_path:
            return

        success = export_config(self._config, Path(file_path))
        if success:
            from ui.toast import Toast
            Toast.success(self._dialog, f"配置已导出到:\n{file_path}")
        else:
            from tkinter import messagebox
            messagebox.showerror(
                "导出失败",
                "无法写入文件，请检查路径权限。",
                parent=self._dialog,
            )

    def _do_import(self) -> None:
        """从 JSON 文件导入配置。"""
        from pathlib import Path
        from tkinter import filedialog, messagebox

        file_path = filedialog.askopenfilename(
            parent=self._dialog,
            title="导入配置",
            filetypes=[("JSON 配置文件", "*.json"), ("所有文件", "*.*")],
        )
        if not file_path:
            return

        imported = import_config(Path(file_path))
        if imported is None:
            messagebox.showerror(
                "导入失败",
                "无法解析所选文件，请确认是有效的配置文件。",
                parent=self._dialog,
            )
            return

        # 询问合并还是覆盖
        choice = messagebox.askyesnocancel(
            "导入选项",
            "是：合并到当前配置（同名快照覆盖）\n"
            "否：完全替换为导入的配置\n"
            "取消：取消导入",
            parent=self._dialog,
        )
        if choice is None:  # 取消
            return
        elif choice:  # 合并
            merged = merge_config(self._config, imported)
            self._config = merged
        else:  # 替换
            self._config = imported

        self._config.save()

        from ui.toast import Toast
        Toast.success(self._dialog, "配置已导入并保存")

        # 关闭对话框，用户重新打开以看到新配置
        self._dialog.destroy()

    def wait(self) -> None:
        """阻塞直到对话框关闭。"""
        self._dialog.wait_window()
