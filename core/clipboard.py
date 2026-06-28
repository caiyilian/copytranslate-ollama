"""剪贴板监听与管理模块。

轮询模式监听系统剪贴板变化，支持内容去重和富文本降级。
"""

from __future__ import annotations

import hashlib
import time
from typing import Callable, Optional

import pyperclip

from core.config import ClipboardConfig


ClipboardCallback = Callable[[str], None]


class ClipboardWatcher:
    """剪贴板监听器。

    定期轮询剪贴板内容，检测变化后触发回调。
    内置去重机制，相同内容不重复触发。

    用法:
        def on_change(text: str) -> None:
            print(f"新内容: {text}")

        watcher = ClipboardWatcher(callback=on_change)
        watcher.start()  # 后台线程启动
        ...
        watcher.stop()
    """

    def __init__(
        self,
        callback: Optional[ClipboardCallback] = None,
        config: Optional[ClipboardConfig] = None,
    ) -> None:
        self._callback = callback
        self._config = config or ClipboardConfig()
        self._running = False
        self._last_text: Optional[str] = None
        self._last_hash: Optional[str] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def poll_interval(self) -> float:
        return self._config.poll_interval_ms / 1000.0

    def _get_clipboard_text(self) -> Optional[str]:
        """获取剪贴板纯文本内容。

        Returns:
            纯文本内容，获取失败返回 None。
        """
        try:
            text = pyperclip.paste()
            if text and isinstance(text, str):
                return text.strip()
            return None
        except Exception:
            return None

    def _compute_hash(self, text: str) -> str:
        """计算文本哈希用于去重。"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]

    def poll_once(self) -> Optional[str]:
        """执行单次轮询检测。

        Returns:
            有新内容返回文本，无变化返回 None。
        """
        text = self._get_clipboard_text()
        if text is None:
            return None

        current_hash = self._compute_hash(text)

        # 首次运行或内容变化
        if self._last_hash is None or current_hash != self._last_hash:
            self._last_text = text
            self._last_hash = current_hash
            return text

        return None

    def poll_loop(self) -> None:
        """轮询主循环（阻塞），供 start() 在后台线程调用。"""
        self._running = True
        while self._running:
            try:
                text = self.poll_once()
                if text is not None and self._callback:
                    self._callback(text)
            except Exception:
                # 防止单次异常导致监听停止
                pass
            time.sleep(self.poll_interval)

    def start(self) -> None:
        """启动监听（阻塞，当前线程进入轮询）。"""
        self.poll_loop()

    def stop(self) -> None:
        """停止监听。"""
        self._running = False

    def read_current(self) -> Optional[str]:
        """读取当前剪贴板内容（不触发回调）。"""
        return self._get_clipboard_text()


def main() -> None:
    """CLI 入口: python -m core.clipboard --watch"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="clipboard")
    parser.add_argument(
        "--watch",
        "-w",
        action="store_true",
        help="启动剪贴板监听模式",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=300,
        help="轮询间隔（毫秒）",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="读取当前剪贴板内容并退出",
    )

    args = parser.parse_args()

    if args.once:
        try:
            text = pyperclip.paste()
            if text:
                print(text)
            else:
                print("(剪贴板为空)")
        except Exception as e:
            print(f"读取剪贴板失败: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.watch:
        config = ClipboardConfig(poll_interval_ms=args.interval)

        def on_change(text: str) -> None:
            text_hash = hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()[:12]
            print(f"[Clipboard] 检测到新内容 (hash: {text_hash})")
            print(f"内容: {text[:200]}")
            if len(text) > 200:
                print(f"... (共 {len(text)} 字符)")
            print("-" * 40)

        watcher = ClipboardWatcher(callback=on_change, config=config)
        print(
            f"剪贴板监听已启动 (间隔: {config.poll_interval_ms}ms)\n"
            "复制任意文本查看效果。按 Ctrl+C 退出。\n"
        )
        try:
            watcher.start()
        except KeyboardInterrupt:
            print("\n监听已停止。")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
