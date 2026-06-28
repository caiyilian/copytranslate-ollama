"""剪贴板监听工作线程。

在后台轮询系统剪贴板，检测到新内容时通过信号通知主线程。
"""

from __future__ import annotations

import hashlib
import time

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication


# 剪贴板轮询间隔（毫秒）
_CLIPBOARD_POLL_MS = 500


class ClipboardWatchWorker(QObject):
    """剪贴板监听工作线程。"""

    clipboard_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._paused = False
        self._last_hash: str = ""

    def run(self) -> None:
        """开始轮询剪贴板（工作线程入口）。"""
        self._running = True
        clipboard = QApplication.clipboard()

        while self._running:
            if not self._paused:
                try:
                    text = clipboard.text()
                    if text:
                        h = hashlib.md5(text.encode("utf-8")).hexdigest()
                        if h != self._last_hash:
                            self._last_hash = h
                            self.clipboard_changed.emit(text)
                except Exception:
                    pass
            time.sleep(_CLIPBOARD_POLL_MS / 1000.0)

    def stop(self) -> None:
        """停止轮询。"""
        self._running = False

    def pause(self) -> None:
        """暂停监听。"""
        self._paused = True

    def resume(self) -> None:
        """恢复监听。"""
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused