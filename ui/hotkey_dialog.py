"""快捷键编辑对话框。

可视化编辑快捷键，支持按键捕获和冲突检测。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Dict, Optional

from core.hotkey_editor import (
    format_hotkey,
    is_valid_hotkey,
    parse_hotkey,
    validate_hotkey,
)


class HotkeyDialog:
    """快捷键编辑对话框。

    用法:
        dialog = HotkeyDialog(parent=root, current_hotkeys={"toggle_window": "Ctrl+Shift+T"})
        dialog.wait()
        if dialog.result:
            print(dialog.result)  # {"toggle_window": "Ctrl+Shift+W"}
    """

    def __init__(
        self,
        parent: tk.Widget,
        current_hotkeys: Dict[str, str],
        on_save: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        self._current = dict(current_hotkeys)
        self._on_save = on_save
        self._result: Optional[Dict[str, str]] = None
        self._editing_var: Optional[tk.StringVar] = None
        self._edit_entry: Optional[ttk.Entry] = None

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("快捷键设置")
        self._dialog.geometry("480x320")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build_ui()

    def _build_ui(self) -> None:
        """构建界面。"""
        frame = ttk.Frame(self._dialog, padding="15")
        frame.pack(fill=tk.BOTH, expand=True)

        # 说明
        ttk.Label(
            frame,
            text="点击快捷键按钮开始捕获，按 Escape 取消。",
            font=("", 9),
            foreground="gray",
        ).pack(anchor=tk.W, pady=(0, 10))

        # 快捷键列表
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        row = 0
        self._entries: Dict[str, tk.StringVar] = {}

        for action, hotkey in sorted(self._current.items()):
            # 动作标签
            ttk.Label(
                list_frame,
                text=self._action_label(action),
                width=18,
                anchor=tk.W,
            ).grid(row=row, column=0, pady=3, padx=(0, 10))

            # 快捷键显示
            var = tk.StringVar(value=hotkey)
            self._entries[action] = var

            entry = ttk.Entry(
                list_frame,
                textvariable=var,
                width=25,
                state="readonly",
            )
            entry.grid(row=row, column=1, pady=3, padx=(0, 10))

            # 编辑 button
            edit_btn = ttk.Button(
                list_frame,
                text="编辑",
                width=6,
                command=lambda a=action, v=var, e=entry: self._start_edit(a, v, e),
            )
            edit_btn.grid(row=row, column=2, pady=3)

            row += 1

        # 底部按钮
        btn_frame = ttk.Frame(self._dialog, padding="5")
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame, text="保存", width=10, command=self._do_save
        ).pack(side=tk.RIGHT, padx=5)
        ttk.Button(
            btn_frame, text="取消", width=10, command=self._dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)

    def _action_label(self, action: str) -> str:
        """获取中文动作名称。"""
        labels = {
            "toggle_window": "显示/隐藏窗口",
            "switch_model": "切换翻译模型",
            "toggle_mode": "切换对照/专注模式",
            "manual_translate": "手动触发翻译",
        }
        return labels.get(action, action)

    def _start_edit(self, action: str, var: tk.StringVar, entry: ttk.Entry) -> None:
        """开始捕获按键。"""
        if self._edit_entry is not None:
            return  # 已经在编辑中

        self._editing_var = var
        self._edit_entry = entry
        entry.configure(state="normal")
        var.set("按按键组合...")
        entry.focus_set()

        entry.bind("<KeyRelease>", lambda e: self._on_key_released(e, action, var, entry))
        entry.bind("<FocusOut>", lambda e: self._cancel_edit(action, var, entry))

    def _on_key_repressed(
        self, event: tk.Event, action: str, var: tk.StringVar, entry: ttk.Entry
    ) -> None:
        """按键释放时捕获。"""
        # 忽略单独的修饰键释放
        if event.keysym in ("Control_L", "Control_R", "Alt_L", "Alt_R", "Shift_L", "Shift_R"):
            return

        # Escape 取消
        if event.keysym in ("Escape", "Esc"):
            self._cancel_edit(action, var, entry)
            return

        parts = []
        if event.state & 0x4:  # Control
            parts.append("Control")
        if event.state & 0x8:  # Alt
            parts.append("Alt")
        if event.state & 0x1:  # Shift
            parts.append("Shift")

        # 获取主键
        key = event.keysym
        if key in ("Control_L", "Control_R", "Alt_L", "Alt_R", "Shift_L", "Shift_R"):
            return

        parts.append(key)
        hotkey_str = format_hotkey(tuple(parts))

        # 验证
        existing = [v for k, v in self._current.items() if k != action]
        valid, error = validate_hotkey(hotkey_str, existing + list(self._entries[k].get() for k in self._entries if k != action))

        if not valid:
            var.set(f"⚠ {error}")
            return

        var.set(hotkey_str)
        self._finish_edit(action, var, entry)

    def _finish_edit(self, action: str, var: tk.StringVar, entry: ttk.Entry) -> None:
        """完成编辑。"""
        entry.configure(state="readonly")
        entry.unbind("<KeyRelease>")
        entry.unbind("<FocusOut>")
        self._editing_var = None
        self._edit_entry = None
        self._current[action] = var.get()

    def _cancel_edit(self, action: str, var: tk.StringVar, entry: ttk.Entry) -> None:
        """取消编辑，恢复原值。"""
        var.set(self._current.get(action, ""))
        entry.configure(state="readonly")
        entry.unbind("<KeyRelease>")
        entry.unbind("<FocusOut>")
        self._editing_var = None
        self._edit_entry = None

    def _do_save(self) -> None:
        """保存修改后的快捷键。"""
        # 验证所有快捷键
        for action, var in self._entries.items():
            hotkey = var.get()
            if not is_valid_hotkey(hotkey):
                messagebox.showerror(
                    "无效快捷键",
                    f"{self._action_label(action)}: {hotkey} 格式无效",
                    parent=self._dialog,
                )
                return

            existing = [v for k, v in self._current.items() if k != action and v != hotkey]
            valid, error = validate_hotkey(hotkey, existing)
            if not valid:
                messagebox.showerror(
                    "快捷键冲突",
                    f"{self._action_label(action)}: {error}",
                    parent=self._dialog,
                )
                return

        self._result = dict(self._current)
        if self._on_save:
            self._on_save(self._result)
        self._dialog.destroy()

    @property
    def result(self) -> Optional[Dict[str, str]]:
        """返回修改后的快捷键字典。"""
        return self._result

    def wait(self) -> None:
        """等待对话框关闭。"""
        self._dialog.wait_window()