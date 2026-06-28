"""ClipboardWatcher 单元测试。"""

from core.clipboard import ClipboardWatcher


class TestClipboardWatcher:
    def test_compute_hash(self) -> None:
        """验证哈希生成。"""
        w = ClipboardWatcher()
        h1 = w._compute_hash("hello world")
        h2 = w._compute_hash("hello world")
        assert h1 == h2
        assert len(h1) == 12

    def test_compute_hash_different(self) -> None:
        """不同内容生成不同哈希。"""
        w = ClipboardWatcher()
        h1 = w._compute_hash("hello")
        h2 = w._compute_hash("world")
        assert h1 != h2

    def test_poll_once_no_callback(self) -> None:
        """轮询不依赖回调。"""
        w = ClipboardWatcher()
        # 首次 poll_once 可能返回 None（剪贴板可能为空）
        result = w.poll_once()
        # 不应抛出异常
        assert result is None or isinstance(result, str)

    def test_stop(self) -> None:
        w = ClipboardWatcher()
        assert w.is_running is False
        w.stop()
        assert w.is_running is False
