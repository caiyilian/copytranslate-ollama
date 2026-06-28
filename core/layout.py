"""窗口布局管理器。

保存和恢复窗口位置、大小、状态（模式、分割器位置等）。
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# 配置文件路径
_LAYOUT_FILE = Path.home() / ".copytranslate-ollama" / "layout.json"

# 全局状态
_lock = threading.Lock()
_observers: List[Callable[[str, Any], None]] = []


# ---------------------------------------------------------------------------
# 核心 API
# ---------------------------------------------------------------------------

def save_layout(
    x: int = 100,
    y: int = 100,
    width: int = 900,
    height: int = 550,
    mode: str = "contrast",
    splitter_ratio: float = 0.5,
    **extra: Any,
) -> bool:
    """保存窗口布局。

    Args:
        x, y: 窗口位置。
        width, height: 窗口大小。
        mode: 当前模式（contrast / focus）。
        splitter_ratio: 分割器位置比例（0-1）。
        **extra: 其他自定义布局数据。

    Returns:
        True 如果保存成功。
    """
    data: Dict[str, Any] = {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "mode": mode,
        "splitter_ratio": splitter_ratio,
        **extra,
    }

    try:
        _LAYOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        _LAYOUT_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        _notify("save", data)
        return True
    except OSError:
        return False


def load_layout() -> Optional[Dict[str, Any]]:
    """加载窗口布局。

    Returns:
        布局字典，如果文件不存在返回 None。
    """
    if not _LAYOUT_FILE.exists():
        return None
    try:
        data = json.loads(_LAYOUT_FILE.read_text(encoding="utf-8"))
        _notify("load", data)
        return data
    except (json.JSONDecodeError, OSError):
        return None


def get_default_layout() -> Dict[str, Any]:
    """获取默认布局。"""
    return {
        "x": 100,
        "y": 100,
        "width": 900,
        "height": 550,
        "mode": "contrast",
        "splitter_ratio": 0.5,
    }


def get_safe_layout(screen_width: int = 1920, screen_height: int = 1080) -> Dict[str, Any]:
    """获取安全的窗口布局（确保窗口在屏幕范围内）。

    Args:
        screen_width: 屏幕宽度。
        screen_height: 屏幕高度。

    Returns:
        调整后的布局字典。
    """
    layout = load_layout() or get_default_layout()

    # 确保窗口大小不超过屏幕
    width = min(layout.get("width", 900), screen_width - 100)
    height = min(layout.get("height", 550), screen_height - 100)

    # 确保位置在屏幕内
    x = max(0, min(layout.get("x", 100), screen_width - width))
    y = max(0, min(layout.get("y", 100), screen_height - height))

    # 确保分割器比例有效
    ratio = layout.get("splitter_ratio", 0.5)
    ratio = max(0.1, min(0.9, ratio))

    return {
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "mode": layout.get("mode", "contrast"),
        "splitter_ratio": ratio,
    }


def delete_layout() -> bool:
    """删除布局配置文件。"""
    if _LAYOUT_FILE.exists():
        try:
            _LAYOUT_FILE.unlink()
            _notify("delete", {})
            return True
        except OSError:
            return False
    return True


def register_observer(callback: Callable[[str, Any], None]) -> None:
    """注册布局变更观察者。"""
    _observers.append(callback)


def unregister_observer(callback: Callable[[str, Any], None]) -> None:
    """移除布局变更观察者。"""
    try:
        _observers.remove(callback)
    except ValueError:
        pass


def _notify(event: str, data: Any) -> None:
    """通知观察者。"""
    for cb in _observers:
        try:
            cb(event, data)
        except Exception:
            pass