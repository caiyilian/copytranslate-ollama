"""翻译流水线。

集成剪贴板监听 → 文本净化 → 翻译调度 → 输出译文的完整流程。
"""

from __future__ import annotations

import re
import signal
import sys
from typing import List, Optional, Tuple

from core.cleaner import TextCleaner
from core.clipboard import ClipboardWatcher
from core.config import AppConfig
from core.logger import HistoryEntry, HistoryManager, log_translation
from core.translator import Translator, _resolve_lang_name


# 分段翻译最大字符数（约 1500 个中文字符或 3000 个英文字符）
_MAX_SEGMENT_CHARS = 2000


def _segment_text(text: str, max_chars: int = _MAX_SEGMENT_CHARS) -> List[str]:
    """将长文本按段落分段。

    优先按空行分段，若单段仍超长则按句子边界切分。

    Args:
        text: 待分段文本。
        max_chars: 每段最大字符数。

    Returns:
        分段后的文本列表。
    """
    # 1. 按空行分段
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

    # 2. 检查每段是否超长，超长则按句子边界切分
    segments: List[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            segments.append(para)
        else:
            # 按句子边界切分（句号、问号、感叹号、换行）
            sentences = re.split(r'(?<=[.!?。！？])\s+|\n+', para)
            current = ""
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                if len(current) + len(sent) + 1 > max_chars:
                    if current:
                        segments.append(current)
                    current = sent
                else:
                    current = (current + " " + sent) if current else sent
            if current:
                segments.append(current)

    return segments if segments else [text]


class Pipeline:
    """翻译流水线。

    管理剪贴板监听、文本净化、翻译调度、输出展示的完整流程。

    用法:
        pipeline = Pipeline()
        pipeline.run_listen(model="translategemma:4b")
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
    ) -> None:
        self._config = config or AppConfig.load()
        self._cleaner = TextCleaner(
            fix_hyphenation=self._config.cleaner.fix_hyphenation,
            merge_paragraph_lines=self._config.cleaner.merge_paragraph_lines,
        )
        self._translator = Translator()
        self._history = HistoryManager()
        self._watcher: Optional[ClipboardWatcher] = None
        self._current_model: Optional[str] = None

    def translate_once(
        self,
        text: str,
        source: str = "en",
        target: str = "zh",
        model: str = "translategemma:4b",
        temperature: float = 0.0,
        max_length: int = 2048,
    ) -> Tuple[str, str]:
        """单次翻译：净化 → 分段翻译 → 记录历史。

        长文本会自动按段落分段翻译后拼接。

        Returns:
            Tuple[str, str]: (译文文本, 检测到的源语言代码)。
        """
        import time

        cleaned = self._cleaner.clean(text)
        start = time.time()

        # 分段翻译
        segments = _segment_text(cleaned)
        if len(segments) == 1:
            result, detected = self._translator.translate(
                text=cleaned,
                source=source,
                target=target,
                model=model,
                temperature=temperature,
                max_length=max_length,
            )
        else:
            # 多段翻译，用空行连接
            translated_parts: List[str] = []
            detected = ""
            for i, seg in enumerate(segments):
                part, det = self._translator.translate(
                    text=seg,
                    source=source,
                    target=target,
                    model=model,
                    temperature=temperature,
                    max_length=max_length,
                )
                translated_parts.append(part)
                if det:
                    detected = det
            result = "\n\n".join(translated_parts)

        self._current_model = model
        duration_ms = (time.time() - start) * 1000

        # 记录日志和历史
        log_translation(
            source_text=cleaned,
            target_text=result,
            source_lang=source,
            target_lang=target,
            model=model,
            duration_ms=duration_ms,
        )
        self._history.add_entry(
            HistoryEntry(
                source_text=cleaned,
                target_text=result,
                source_lang=source,
                target_lang=target,
                model=model,
                detected_lang=detected if source == "auto" else "",
                duration_ms=duration_ms,
            )
        )

        return result, detected

    def stop_current_model(self) -> None:
        """卸载当前已加载的模型（切换模型前调用）。"""
        if self._current_model:
            try:
                self._translator._client.stop_model(self._current_model)
            except Exception:
                pass  # 卸载失败不影响后续操作

    def run_listen(
        self,
        model: Optional[str] = None,
        source: str = "auto",
        target: str = "zh",
    ) -> None:
        """启动剪贴板监听翻译模式。

        Args:
            model: 模型名称，默认从配置读取。
            source: 源语言。
            target: 目标语言。
        """
        cfg = self._config
        model_name = model or cfg.translation.active_model
        source_lang = source if source != "auto" else cfg.translation.source_lang
        target_lang = target or cfg.translation.target_lang
        temperature = cfg.translation.temperature
        max_length = cfg.translation.max_length

        print(
            f"CopyTranslator-Ollama 翻译监听已启动\n"
            f"  模型: {model_name}\n"
            f"  方向: {source_lang} -> {target_lang}\n"
            f"  净化: {'开' if cfg.clipboard.enable_cleaner else '关'}\n"
            f"  状态: 等待剪贴板内容...\n"
            f"  提示: 复制任意文本开始翻译，按 Ctrl+C 退出\n"
            f"{'─' * 50}"
        )

        def on_clipboard_change(raw_text: str) -> None:
            """剪贴板变化回调。"""
            nonlocal source_lang

            try:
                # 文本净化
                text = raw_text
                if cfg.clipboard.enable_cleaner:
                    text = self._cleaner.clean(raw_text)

                # 翻译（自动检测语言）
                result, detected = self._translator.translate(
                    text=text,
                    source=source_lang,
                    target=target_lang,
                    model=model_name,
                    temperature=temperature,
                    max_length=max_length,
                )

                # 显示检测到的语言
                detected_label = _resolve_lang_name(detected) if detected != source_lang else ""

                # 输出
                print(f"\n[原文]    {text[:200]}")
                if len(text) > 200:
                    print(f"          ... (共 {len(text)} 字符)")
                if detected_label:
                    print(f"[检测到]  {detected_label}")
                print(f"[译文]    {result[:200]}")
                if len(result) > 200:
                    print(f"          ... (共 {len(result)} 字符)")
                print(f"{'─' * 50}")

            except Exception as e:
                print(f"\n[错误] 翻译失败: {e}")
                print(f"{'─' * 50}")

        self._watcher = ClipboardWatcher(
            callback=on_clipboard_change,
            config=cfg.clipboard,
        )

        def handle_signal(signum: int, frame: object) -> None:
            """信号处理，优雅退出。"""
            print("\n正在退出...")
            if self._watcher:
                self._watcher.stop()
            self._translator.close()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        try:
            self._watcher.start()
        except KeyboardInterrupt:
            print("\n正在退出...")
        finally:
            if self._watcher:
                self._watcher.stop()
            self._translator.close()

    def close(self) -> None:
        """释放资源。"""
        if self._watcher:
            self._watcher.stop()
        self._translator.close()
