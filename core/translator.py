"""翻译调度器。

根据模型和语言方向选择合适的 prompt 模板，调用 Ollama 客户端完成翻译。
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Dict, Optional, Tuple

from core.lang_detector import detect_language
from core.ollama_client import OllamaClient, OllamaError


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

PROMPT_TEMPLATES: Dict[str, str] = {
    "translategemma": (
        "<bos>You are a professional {source} to {target} translator. "
        "Your goal is to accurately convey the meaning and nuances "
        "of the original {source} text while adhering to {target} "
        "grammar, vocabulary, and cultural sensitivities. "
        "Produce only the {target} translation, "
        "without any additional explanations or commentary.\n"
        "Please translate the following {source} text into {target}: "
        "{text}"
    ),
    "standard": (
        "Translate the following {source} text to {target}: {text}"
    ),
}


def _resolve_template(model: str) -> str:
    """根据模型名称选择 prompt 模板。"""
    model_lower = model.lower()
    if "translategemma" in model_lower:
        return PROMPT_TEMPLATES["translategemma"]
    return PROMPT_TEMPLATES["standard"]


# 语言名称映射（ISO 代码 -> 中文名称）
LANG_NAMES: Dict[str, str] = {
    "en": "英语",
    "zh": "简体中文",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "ar": "阿拉伯语",
    "pt": "葡萄牙语",
    "it": "意大利语",
    "vi": "越南语",
    "th": "泰语",
    "hi": "印地语",
}


def _resolve_lang_name(code: str) -> str:
    """将语言代码转为完整名称。"""
    return LANG_NAMES.get(code, code)


def resolve_source(source: str, text: str) -> str:
    """解析源语言：如果为 'auto'，使用语言检测自动识别。

    Args:
        source: 用户指定的源语言代码或 'auto'。
        text: 待翻译文本。

    Returns:
        解析后的语言代码（如 'en', 'zh'）。
    """
    if source != "auto":
        return source
    lang, _ = detect_language(text)
    return lang


def build_prompt(
    text: str,
    source: str,
    target: str,
    model: str = "translategemma:4b",
) -> str:
    """构建翻译 prompt。

    Args:
        text: 待翻译文本。
        source: 源语言代码（如 'en'），支持 'auto' 自动检测。
        target: 目标语言代码（如 'zh'）。
        model: 模型名称，用于选择模板。

    Returns:
        完整 prompt 字符串。
    """
    resolved_source = resolve_source(source, text)
    template = _resolve_template(model)
    source_name = _resolve_lang_name(resolved_source)
    target_name = _resolve_lang_name(target)
    return template.format(
        source=source_name,
        target=target_name,
        text=text,
    )


# ---------------------------------------------------------------------------
# 响应后处理
# ---------------------------------------------------------------------------

# 需要去除的常见额外说明前缀
_EXTRANEOUS_PREFIXES = [
    re.compile(
        r"^(Sure|Of course|Certainly)[,.:\s]+"
        r"(here is|here's)?[\s,]*(the\s+)?translation[\s\S]*?[:\s-]+",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(Here is|Here's)[\s,]*(the\s+)?translation[\s\S]*?[:\s-]+",
        re.IGNORECASE,
    ),
    re.compile(r"^(Translation|Translate)[:\s]+", re.IGNORECASE),
    re.compile(r"^The translation (is|of).*?[:\s]+", re.IGNORECASE),
    re.compile(r"^In\s+\w+[,:]\s*", re.IGNORECASE),
]


def clean_response(response: str) -> str:
    """清理翻译响应，去除模型的额外说明文字。

    只保留最纯净的译文文本。
    """
    text = response.strip()

    # 尝试去除常见的前缀
    for _ in range(3):
        cleaned = text
        for pattern in _EXTRANEOUS_PREFIXES:
            cleaned = pattern.sub("", cleaned).strip()
        if cleaned == text:
            break
        text = cleaned

    # 去除引号包裹
    if (text.startswith('"') and text.endswith('"')) or (
        text.startswith("'") and text.endswith("'")
    ):
        text = text[1:-1].strip()

    return text


# ---------------------------------------------------------------------------
# 翻译调度器
# ---------------------------------------------------------------------------


class Translator:
    """翻译调度器。

    管理模型选择、prompt 构建、响应解析、重试和降级。
    """

    def __init__(self, client: Optional[OllamaClient] = None) -> None:
        self._client = client or OllamaClient()

    def translate(
        self,
        text: str,
        source: str = "en",
        target: str = "zh",
        model: str = "translategemma:4b",
        temperature: float = 0.0,
        max_length: int = 2048,
    ) -> Tuple[str, str]:
        """执行单次翻译。

        Args:
            text: 待翻译文本。
            source: 源语言代码，支持 'auto' 自动检测。
            target: 目标语言代码。
            model: 模型名称。
            temperature: 温度参数。
            max_length: 最大生成长度。

        Returns:
            Tuple[str, str]: (译文文本, 检测到的源语言代码)。

        Raises:
            OllamaError: 翻译失败。
        """
        resolved = resolve_source(source, text)
        prompt = build_prompt(text, source, target, model)
        result = self._client.generate(
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_length=max_length,
        )
        return clean_response(result.response), resolved

    def translate_stream(
        self,
        text: str,
        source: str = "en",
        target: str = "zh",
        model: str = "translategemma:4b",
        temperature: float = 0.0,
        max_length: int = 2048,
    ):
        """流式翻译，逐块 yield 译文。

        Yields:
            翻译文本片段。
        """
        resolved = resolve_source(source, text)
        prompt = build_prompt(text, source, target, model)
        yield from self._client.generate_stream(
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_length=max_length,
        )

    def close(self) -> None:
        """释放资源。"""
        self._client.close()


def main() -> None:
    """CLI 入口: python -m core.translator"""
    parser = argparse.ArgumentParser(prog="translator")
    parser.add_argument("--text", "-t", required=True, help="待翻译文本")
    parser.add_argument("--model", "-m", default="translategemma:4b", help="模型名称")
    parser.add_argument("--source", "-s", default="en", help="源语言代码")
    parser.add_argument("--target", "-tg", default="zh", help="目标语言代码")
    parser.add_argument("--temperature", type=float, default=0.0, help="温度参数")
    parser.add_argument("--stream", action="store_true", help="流式输出")

    args = parser.parse_args()

    translator = Translator()
    try:
        if args.stream:
            print(f"[{args.model}] ", end="", flush=True)
            for chunk in translator.translate_stream(
                args.text,
                source=args.source,
                target=args.target,
                model=args.model,
                temperature=args.temperature,
            ):
                print(chunk, end="", flush=True)
            print()
        else:
            result = translator.translate(
                args.text,
                source=args.source,
                target=args.target,
                model=args.model,
                temperature=args.temperature,
            )
            print(result)
    except OllamaError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        translator.close()


if __name__ == "__main__":
    main()