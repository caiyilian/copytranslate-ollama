"""系统托盘模块。

使用 Windows Shell_NotifyIcon API 实现系统托盘常驻图标。
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable, Optional

import win32api
import win32con
import win32gui
from PIL import Image, ImageDraw


# 托盘自定义消息
_WM_TRAYICON = win32con.WM_USER + 100


class SystemTray:
    """系统托盘图标。

    基于 Windows Shell_NotifyIcon API 实现。
    支持右键弹出菜单、左键点击回调。

    用法:
        tray = SystemTray(
            tooltip="CopyTranslator-Ollama",
            on_show=lambda: window.show(),
            on_quit=lambda: exit(),
        )
        tray.create()
        ...
        tray.destroy()
    """

    def __init__(
        self,
        tooltip: str = "CopyTranslator-Ollama",
        on_show: Optional[Callable[[], None]] = None,
        on_focus: Optional[Callable[[], None]] = None,
        on_toggle_pause: Optional[Callable[[], None]] = None,
        on_quit: Optional[Callable[[], None]] = None,
        on_switch_model: Optional[Callable[[], None]] = None,
    ) -> None:
        self._tooltip = tooltip
        self._on_show = on_show
        self._on_focus = on_focus
        self._on_toggle_pause = on_toggle_pause
        self._on_quit = on_quit
        self._on_switch_model = on_switch_model

        self._hwnd: Optional[int] = None
        self._icon_id = 0
        self._paused = False
        self._visible = True

    def _create_icon(self) -> int:
        """创建 16x16 托盘图标。"""
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 绘制一个简单的翻译图标 "T"
        draw.rectangle([0, 0, 15, 15], fill=(50, 120, 200, 255))
        draw.text((3, 1), "T", fill=(255, 255, 255, 255))
        return win32gui.CreateBitmapFromImage(
            img.tobytes(), 16, 16, 4 * 16, 4
        )

    @staticmethod
    def _create_menu_item(
        menu: int,
        text: str,
        item_id: int,
        checked: bool = False,
        enabled: bool = True,
    ) -> None:
        """添加菜单项。"""
        flags = win32con.MF_STRING
        if not enabled:
            flags |= win32con.MF_GRAYED
        if checked:
            flags |= win32con.MF_CHECKED
        win32gui.AppendMenu(menu, flags, item_id, text)

    def _show_context_menu(self) -> None:
        """显示右键上下文菜单。"""
        if not self._hwnd:
            return

        menu = win32gui.CreatePopupMenu()

        item_id = 1001
        self._create_menu_item(
            menu,
            f"{'✓ ' if self._visible else ''}显示/隐藏窗口",
            item_id,
        )

        item_id = 1002
        self._create_menu_item(menu, "专注模式", item_id)

        item_id = 1003
        self._create_menu_item(
            menu,
            f"{'⏸ ' if self._paused else '▶ '}"
            f"{'恢复' if self._paused else '暂停'}监听",
            item_id,
        )

        item_id = 1004
        self._create_menu_item(menu, "切换模型", item_id)

        item_id = 2000
        self._create_menu_item(menu, "", item_id, enabled=False)

        item_id = 3001
        self._create_menu_item(menu, "退出", item_id)

        # 获取鼠标位置显示菜单
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self._hwnd)
        cmd = win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON | win32con.TPM_RETURNCMD,
            pos[0],
            pos[1],
            0,
            self._hwnd,
            None,
        )

        win32gui.DestroyMenu(menu)

        # 处理菜单命令
        if cmd == 1001 and self._on_show:
            self._on_show()
        elif cmd == 1002 and self._on_focus:
            self._on_focus()
        elif cmd == 1003 and self._on_toggle_pause:
            self._on_toggle_pause()
        elif cmd == 1004 and self._on_switch_model:
            self._on_switch_model()
        elif cmd == 3001 and self._on_quit:
            self._on_quit()

    def _wnd_proc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        """窗口消息处理。"""
        if msg == _WM_TRAYICON:
            if lparam == win32con.WM_RBUTTONUP:
                self._show_context_menu()
            elif lparam == win32con.WM_LBUTTONUP:
                if self._on_show:
                    self._on_show()
            return 0
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def create(self) -> None:
        """创建托盘图标和隐藏窗口。"""
        # 注册窗口类
        hinstance = win32api.GetModuleHandle(None)
        wc = win32gui.WNDCLASS()
        wc.hInstance = hinstance
        wc.lpszClassName = "CopyTranslatorTrayClass"
        wc.lpfnWndProc = self._wnd_proc
        class_atom = win32gui.RegisterClass(wc)

        # 创建隐藏窗口用于接收消息
        self._hwnd = win32gui.CreateWindow(
            class_atom,
            "CopyTranslatorTray",
            win32con.WS_OVERLAPPEDWINDOW,
            0,
            0,
            0,
            0,
            0,
            0,
            hinstance,
            None,
        )

        # 创建图标
        icon = self._create_icon()

        # 添加托盘图标
        nid = (
            self._hwnd,
            self._icon_id,
            win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP,
            _WM_TRAYICON,
            icon,
            self._tooltip,
        )
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

    def destroy(self) -> None:
        """销毁托盘图标。"""
        if self._hwnd:
            nid = (self._hwnd, self._icon_id)
            win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, nid)
            win32gui.DestroyWindow(self._hwnd)
            self._hwnd = None

    def set_status(self, paused: bool, visible: bool) -> None:
        """更新状态。"""
        self._paused = paused
        self._visible = visible

    def set_tooltip(self, text: str) -> None:
        """更新工具提示。"""
        self._tooltip = text
        # 简化实现：重新创建图标可更新 tooltip，此处略