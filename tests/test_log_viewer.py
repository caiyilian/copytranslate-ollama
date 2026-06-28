"""Log Viewer 日志查看器单元测试。"""

import tempfile
from pathlib import Path
from typing import List

from core.log_viewer import (
    LogEntry,
    clear_logs,
    count_logs,
    get_file_size,
    parse_log_line,
    read_logs,
)


def _write_log_file(path: Path, lines: List[str]) -> None:
    path.write_text("\n".join(lines), encoding="utf-8")


class TestParseLogLine:
    """测试日志行解析。"""

    def test_valid_info_line(self) -> None:
        line = "2025-06-28 10:00:00 [INFO] copytranslate: TRANSLATE model=m1 en->zh len=5"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.level == "INFO"
        assert entry.logger_name == "copytranslate"
        assert "TRANSLATE" in entry.message

    def test_valid_error_line(self) -> None:
        line = "2025-06-28 10:00:00 [ERROR] core: Something broke"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.level == "ERROR"

    def test_valid_warning_line(self) -> None:
        line = "2025-06-28 10:00:00 [WARNING] core: Low memory"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.level == "WARNING"

    def test_invalid_line(self) -> None:
        assert parse_log_line("not a log line") is None

    def test_timestamp_parsing(self) -> None:
        line = "2025-06-28 10:00:00 [INFO] name: msg"
        entry = parse_log_line(line)
        assert entry is not None
        assert entry.timestamp.year == 2025
        assert entry.timestamp.month == 6
        assert entry.timestamp.hour == 10


class TestReadLogs:
    """测试日志读取和过滤。"""

    def setup_method(self) -> None:
        self._tmp = Path(tempfile.mktemp(suffix=".log"))
        _write_log_file(self._tmp, [
            "2025-06-28 10:00:00 [INFO] copytranslate: TRANSLATE model=m1",
            "2025-06-28 10:01:00 [WARNING] core: Slow response",
            "2025-06-28 10:02:00 [ERROR] ollama: Connection failed",
            "2025-06-28 10:03:00 [INFO] copytranslate: TRANSLATE model=m2",
            "invalid line",
        ])

    def teardown_method(self) -> None:
        if self._tmp.exists():
            self._tmp.unlink()

    def test_read_all(self) -> None:
        entries = read_logs(self._tmp)
        # 4 valid entries
        assert len(entries) == 4

    def test_newest_first(self) -> None:
        entries = read_logs(self._tmp)
        # 最新在前
        assert entries[0].timestamp > entries[-1].timestamp

    def test_level_filter(self) -> None:
        entries = read_logs(self._tmp, level_filter="INFO")
        assert len(entries) == 2
        assert all(e.level == "INFO" for e in entries)

    def test_keyword_filter(self) -> None:
        entries = read_logs(self._tmp, keyword="m1")
        assert len(entries) == 1
        assert "m1" in entries[0].message

    def test_keyword_case_insensitive(self) -> None:
        entries = read_logs(self._tmp, keyword="TRANSLATE")
        assert len(entries) == 2

    def test_limit(self) -> None:
        entries = read_logs(self._tmp, limit=2)
        assert len(entries) == 2

    def test_offset(self) -> None:
        entries = read_logs(self._tmp, offset=2)
        assert len(entries) == 2

    def test_nonexistent_file(self) -> None:
        entries = read_logs(Path("/nonexistent/file.log"))
        assert entries == []

    def test_empty_file(self) -> None:
        empty = Path(tempfile.mktemp(suffix=".log"))
        empty.write_text("", encoding="utf-8")
        try:
            entries = read_logs(empty)
            assert entries == []
        finally:
            empty.unlink()


class TestCountLogs:
    """测试日志条数统计。"""

    def setup_method(self) -> None:
        self._tmp = Path(tempfile.mktemp(suffix=".log"))
        _write_log_file(self._tmp, [
            "2025-06-28 10:00:00 [INFO] copytranslate: msg1",
            "2025-06-28 10:01:00 [WARNING] core: warn",
            "2025-06-28 10:02:00 [ERROR] ollama: fail",
        ])

    def teardown_method(self) -> None:
        if self._tmp.exists():
            self._tmp.unlink()

    def test_count_all(self) -> None:
        assert count_logs(self._tmp) == 3

    def test_count_filtered(self) -> None:
        assert count_logs(self._tmp, level_filter="ERROR") == 1

    def test_count_keyword(self) -> None:
        assert count_logs(self._tmp, keyword="warn") == 1


class TestGetFileSize:
    """测试文件大小获取。"""

    def test_existing_file(self) -> None:
        tmp = Path(tempfile.mktemp(suffix=".log"))
        tmp.write_text("hello", encoding="utf-8")
        try:
            assert get_file_size(tmp) == 5
        finally:
            tmp.unlink()

    def test_nonexistent_file(self) -> None:
        assert get_file_size(Path("/nonexistent/file.log")) == 0


class TestClearLogs:
    """测试日志清空。"""

    def test_clear(self) -> None:
        tmp = Path(tempfile.mktemp(suffix=".log"))
        tmp.write_text("some log content", encoding="utf-8")
        assert clear_logs(tmp) is True
        assert tmp.read_text(encoding="utf-8") == ""
        tmp.unlink()

    def test_clear_nonexistent(self) -> None:
        assert clear_logs(Path("/nonexistent/file.log")) is True