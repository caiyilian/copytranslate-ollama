"""OllamaClient 单元测试。"""

from core.ollama_client import (
    OllamaClient,
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    _format_size,
)


def test_format_size_bytes() -> None:
    assert _format_size(500) == "500 B"


def test_format_size_kb() -> None:
    assert _format_size(2048) == "2.0 KB"


def test_format_size_mb() -> None:
    size = 5 * 1024 * 1024
    assert _format_size(size) == "5.0 MB"


def test_format_size_gb() -> None:
    size = 3 * 1024 * 1024 * 1024
    assert _format_size(size) == "3.00 GB"