"""配置快照管理对话框。

允许用户列出、保存、加载和删除配置快照（预设）。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional

from core.config import AppConfig
from core.snapshot_manager import SnapshotManager, SnapshotError


class SnapshotDialog:
    """快照管理对话框。

    用法:
        dialog = SnapshotDialog(parent=root, config=config,
                                on_select=lambda name: ...)
        dialog.wait()
    """

    def __init__(
        self,
        parent: tk.Widget,
        config: AppConfig,
        on_select: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._config = config
        self._manager = SnapshotManager(config)
        self._on_select = on_select
        self._result: Optional[str] = None

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("配置快照管理")
        self._dialog.geometry("480x380")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()
        self._refresh_list()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        """构建对话框界面。"""
        # 说明
        ttk.Label(
            self._dialog,
            text="快照是可切换的翻译配置预设，包含模型、语言方向、模式等设置。",
            wraplength=440,
        ).pack(pady=(10, 5), padx=20, anchor=tk.W)

        # 列表区域
        list_frame = ttk.LabelFrame(self._dialog, text="可用快照", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        self._listbox = tk.Listbox(list_frame, height=8)
        self._listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self._listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._listbox.configure(yscrollcommand=scrollbar.set)

        # 双击加载
        self._listbox.bind("<Double-Button-1>", lambda e: self._do_load())

        # 按钮区域
        btn_frame = ttk.Frame(self._dialog, padding="5")
        btn_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        # 左侧：操作按钮
        left_btns = ttk.Frame(btn_frame)
        left_btns.pack(side=tk.LEFT)

        ttk.Button(
            left_btns, text="加载", width=8, command=self._do_load
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            left_btns, text="保存当前", width=8, command=self._do_save
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(
            left_btns, text="删除", width=8, command=self._do_delete
        ).pack(side=tk.LEFT, padx=2)

        # 右侧：关闭
        ttk.Button(
            btn_frame, text="关闭", width=8, command=self._dialog.destroy
        ).pack(side=tk.RIGHT, padx=2)

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        """刷新快照列表显示。"""
        self._listbox.delete(0, tk.END)
        for snap in self._manager.list_snapshots():
            self._listbox.insert(
                tk.END,
                f"{snap.name}  [{snap.model}]  {snap.source_lang}→{snap.target_lang}  ({snap.mode})",
            )

    def _get_selected_name(self) -> Optional[str]:
        """获取当前选中的快照名称。"""
        sel = self._listbox.curselection()
        if not sel:
            messagebox.showwarning("提示", "请先选择一个快照", parent=self._dialog)
            return None
        return self._manager.list_snapshots()[sel[0]].name

    def _do_load(self) -> None:
        """加载选中快照。"""
        name = self._get_selected_name()
        if name is None:
            return

        success = self._manager.apply_snapshot(name, self._config)
        if success:
            self._config.save()
            if self._on_select:
                self._on_select(name)
            self._dialog.destroy()
        else:
            messagebox.showerror("错误", f"无法加载快照 '{name}'", parent=self._dialog)

    def _do_save(self) -> None:
        """将当前配置保存为新快照。"""
        dialog = _SaveSnapshotDialog(self._dialog, self._manager)
        dialog.wait()
        if dialog.result:
            name = dialog.result
            try:
                self._manager.save_current_as(name, self._config, override=True)
                self._refresh_list()
            except SnapshotError as e:
                messagebox.showerror("错误", str(e), parent=self._dialog)

    def _do_delete(self) -> None:
        """删除选中快照。"""
        name = self._get_selected_name()
        if name is None:
            return

        if messagebox.askyesno(
            "确认删除", f"确定删除快照 '{name}' 吗？", parent=self._dialog
        ):
            self._manager.remove_snapshot(name)
            self._refresh_list()

    # ------------------------------------------------------------------
    # 外部接口
    # ------------------------------------------------------------------

    @property
    def result(self) -> Optional[str]:
        """返回最后加载的快照名称。"""
        return self._result

    def wait(self) -> None:
        """等待对话框关闭。"""
        self._dialog.wait_window()


class _SaveSnapshotDialog:
    """保存快照的输入对话框。"""

    def __init__(self, parent: tk.Toplevel, manager: SnapshotManager) -> None:
        self._manager = manager
        self.result: Optional[str] = None

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("保存快照")
        self._dialog.geometry("360x140")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        ttk.Label(
            self._dialog, text="快照名称："
        ).pack(pady=(15, 5), padx=20, anchor=tk.W)

        self._name_var = tk.StringVar()
        self._entry = ttk.Entry(
            self._dialog, textvariable=self._name_var, width=40
        )
        self._entry.pack(padx=20, pady=5)
        self._entry.focus_set()
        self._entry.bind("<Return>", lambda e: self._do_save())

        btn_frame = ttk.Frame(self._dialog)
        btn_frame.pack(pady=10)

        ttk.Button(
            btn_frame, text="保存", width=8, command=self._do_save
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame, text="取消", width=8, command=self._dialog.destroy
        ).pack(side=tk.LEFT, padx=5)

    def _do_save(self) -> None:
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("提示", "请输入快照名称", parent=self._dialog)
            return
        # 检查同名
        if self._manager.get_snapshot(name) is not None:
            if not messagebox.askyesno(
                "覆盖确认",
                f"快照 '{name}' 已存在，是否覆盖？",
                parent=self._dialog,
            ):
                return
        self.result = name
        self._dialog.destroy()
