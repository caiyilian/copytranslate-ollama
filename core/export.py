"""翻译服务模块。

将历史翻译记录导出为 TXT / CSV / JSON 文件。
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import List

from core.logger import HistoryManager, HistoryEntry


def _format_entry_txt(entry: HistoryEntry, index: int) -> str:
    """格式化为 TXT 单条。"""
    ts = entry.timestamp[:19]
    lang = f"{entry.source_lang}->{entry.target_lang}"
    return (
        f"[{index}] {ts} | {entry.model} | {lang}\n"
        f"原文: {entry.source_text}\n"
        f"译文: {entry.target_text}\n"
    )


def export_to_txt(
    entries: List[HistoryEntry],
    file_path: Path,
) -> bool:
    """导出为 TXT 文件。"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"翻译记录导出 - {datetime.now():%Y-%m-%d %H:%M}\n")
            f.write(f"共 {len(entries)} 条\n{'=' * 40}\n\n")
            for i, entry in enumerate(entries, 1):
                f.write(_format_entry_txt(entry, i))
                f.write("\n")
        return True
    except OSError:
        return False


def export_to_csv(
    entries: List[HistoryEntry],
    file_path: Path,
) -> bool:
    """导出为 CSV 文件。"""
    try:
        with open(file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "序号", "时间", "模型", "源语言", "目标语言",
                "原文", "译文", "耗时ms",
            ])
            for i, entry in enumerate(entries, 1):
                writer.writerow([
                    i,
                    entry.timestamp[:19],
                    entry.model,
                    entry.source_lang,
                    entry.target_lang,
                    entry.source_text,
                    entry.target_text,
                    f"{entry.duration_ms:.0f}",
                ])
        return True
    except OSError:
        return False


def export_to_json(
    entries: List[HistoryEntry],
    file_path: Path,
) -> bool:
    """导出为 JSON 文件。"""
    data = {
        "exported_at": datetime.now().isoformat(),
        "total": len(entries),
        "entries": [e.to_dict() for e in entries],
    }
    try:
        file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
    except OSError:
        return False


def export_entries(
    entries: List[HistoryEntry],
    file_path: Path,
    fmt: str = "txt",
) -> bool:
    """导出条目到文件。

    Args:
        entries: 要导出的历史条目。
        file_path: 目标路径（扩展名会被自动修正）。
        fmt: 格式 - "txt" / "csv" / "json"。

    Returns:
        True 如果成功。
    """
    fmt = fmt.lower()
    # 修正扩展名
    ext_map = {"txt": ".txt", "csv": ".csv", "json": ".json"}
    correct_ext = ext_map.get(fmt, ".txt")
    if file_path.suffix.lower() != correct_ext:
        file_path = file_path.with_suffix(correct_ext)

    if fmt == "txt":
        return export_to_txt(entries, file_path)
    elif fmt == "csv":
        return export_to_csv(entries, file_path)
    elif fmt == "json":
        return export_to_json(entries, file_path)
    return False


def get_export_entries(
    history_manager: HistoryManager | None = None,
    limit: int = 1000,
) -> List[HistoryEntry]:
    """获取要导出的条目。"""
    hm = history_manager or HistoryManager()
    return hm.list_entries(limit=limit)