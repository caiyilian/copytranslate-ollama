"""语言自动检测模块。

基于 Unicode 字符范围和常见词汇特征进行规则检测。
无需外部模型或网络调用，支持 pip 不可用时的离线使用。

支持的语言:
    en (英语), zh (中文), ja (日语), ko (韩语),
    fr (法语), de (德语), es (西班牙语), ru (俄语),
    ar (阿拉伯语), pt (葡萄牙语), th (泰语)
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Unicode 区间定义
# ---------------------------------------------------------------------------

# CJK 统一表意文字（中日韩共享）
CJK_UNIFIED = range(0x4E00, 0x9FFF + 1)
CJK_EXT_A = range(0x3400, 0x4DBF + 1)
CJK_EXT_B = range(0x20000, 0x2A6DF + 1)

# 日语特有字符
HIRAGANA = range(0x3040, 0x309F + 1)  # 平假名
KATAKANA = range(0x30A0, 0x30FF + 1)  # 片假名
KATAKANA_PHONETIC = range(0x31F0, 0x31FF + 1)  # 片假名语音扩展

# 韩语谚文音节
HANGUL_SYLLABLES = range(0xAC00, 0xD7AF + 1)
HANGUL_JAMO = range(0x1100, 0x11FF + 1)
HANGUL_COMPAT_JAMO = range(0x3130, 0x318F + 1)

# 阿拉伯语
ARABIC = range(0x0600, 0x06FF + 1)
ARABIC_SUPPLEMENT = range(0x0750, 0x077F + 1)
ARABIC_EXT_A = range(0x08A0, 0x08FF + 1)

# 泰语
THAI = range(0x0E00, 0x0E7F + 1)

# 西里尔字母（俄语等）
CYRILLIC = range(0x0400, 0x04FF + 1)
CYRILLIC_SUPPLEMENT = range(0x0500, 0x052F + 1)

# 拉丁字母补充（法语、德语、西班牙语、葡萄牙语等使用的带变音符号的拉丁字母）
LATIN_1_SUPPLEMENT = range(0x00C0, 0x00FF + 1)  # À-ÿ
LATIN_EXT_A = range(0x0100, 0x017F + 1)
LATIN_EXT_B = range(0x0180, 0x024F + 1)


# ---------------------------------------------------------------------------
# Unicode 块检测函数
# ---------------------------------------------------------------------------


def _char_in_ranges(char: str, *ranges: range) -> bool:
    """检查字符是否在任意一个 Unicode 区间内。"""
    code = ord(char)
    for r in ranges:
        if code in r:
            return True
    return False


def _count_in_ranges(text: str, *ranges: range) -> int:
    """统计文本中落在指定区间内的字符数。"""
    return sum(1 for ch in text if _char_in_ranges(ch, *ranges))


def _has_cjk(text: str) -> int:
    """统计 CJK 统一表意文字字符数。"""
    return _count_in_ranges(text, CJK_UNIFIED, CJK_EXT_A, CJK_EXT_B)


def _has_hiragana(text: str) -> int:
    """统计平假名字符数。"""
    return _count_in_ranges(text, HIRAGANA)


def _has_katakana(text: str) -> int:
    """统计片假名字符数。"""
    return _count_in_ranges(text, KATAKANA, KATAKANA_PHONETIC)


def _has_hangul(text: str) -> int:
    """统计韩文字符数。"""
    return _count_in_ranges(text, HANGUL_SYLLABLES, HANGUL_JAMO, HANGUL_COMPAT_JAMO)


def _has_arabic(text: str) -> int:
    """统计阿拉伯文字符数。"""
    return _count_in_ranges(text, ARABIC, ARABIC_SUPPLEMENT, ARABIC_EXT_A)


def _has_thai(text: str) -> int:
    """统计泰文字符数。"""
    return _count_in_ranges(text, THAI)


def _has_cyrillic(text: str) -> int:
    """统计西里尔字符数。"""
    return _count_in_ranges(text, CYRILLIC, CYRILLIC_SUPPLEMENT)


def _has_latin_ext(text: str) -> int:
    """统计扩展拉丁字符数（排除基础 ASCII 字母）。"""
    return _count_in_ranges(text, LATIN_1_SUPPLEMENT, LATIN_EXT_A, LATIN_EXT_B)


# ---------------------------------------------------------------------------
# 欧洲语言常见词特征（用于区分 en/fr/de/es/pt）
# ---------------------------------------------------------------------------

# 各语言的高频词（用于区分同属拉丁字母体系的欧洲语言）
_LANG_COMMON_WORDS: Dict[str, List[str]] = {
    "en": [
        "the", "and", "for", "are", "but", "not", "you", "all", "can",
        "had", "her", "was", "one", "our", "out", "has", "have", "been",
        "some", "them", "than", "that", "this", "very", "what", "when",
        "where", "which", "while", "will", "with", "would", "your",
        "about", "could", "should", "their", "there", "these", "they",
        "thing", "think", "those", "through", "under", "until", "upon",
        "well", "were", "after", "also", "because", "before", "being",
        "between", "does", "doing", "don", "every", "going", "here",
        "just", "know", "like", "made", "make", "more", "most", "much",
        "must", "need", "never", "now", "only", "other", "over", "own",
        "people", "place", "right", "said", "same", "say", "should",
        "still", "such", "take", "tell", "thing", "time", "too", "two",
        "way", "year", "years",
    ],
    "fr": [
        "dans", "avec", "pour", "elle", "ils", "leur", "mais", "plus",
        "tout", "bien", "fait", "faire", "nous", "vous", "elles",
        "aussi", "donc", "sans", "alors", "peut", "tres", "très",
        "comme", "être", "avoir", "cette", "leurs", "autre", "même",
        "entre", "monde", "encore", "deux", "premiere", "première",
        "grand", "pendant", "aucun", "chaque", "parce", "que", "qui",
        "dont", "où", "sur", "dans", "avec", "pour", "sont", "cela",
        "cette", "jetaient", "était", "étaient", "le", "la", "les",
        "un", "une", "des", "ce", "ces", "en", "y", "son", "sa",
        "mes", "tes", "ses", "nos", "vos", "leurs",
    ],
    "de": [
        "und", "die", "das", "nicht", "sich", "auch", "sein", "noch",
        "nur", "muss", "werden", "durch", "sehr", "ihre", "ihrer",
        "gegen", "ohne", "nach", "uber", "über", "dies", "wieder",
        "wurde", "wurden", "unter", "beim", "kann", "zwei", "zwischen",
        "dieser", "diese", "dieses", "einem", "einen", "einer",
        "eines", "seine", "seiner", "seinen", "einem", "keine",
        "auf", "bei", "bin", "bis", "hat", "hier", "immer", "ist",
        "mit", "schon", "schön", "sind", "soll", "sondern",
    ],
    "es": [
        "que", "los", "las", "pero", "mas", "más", "son", "esta",
        "está", "este", "como", "para", "entre", "todo", "tambien",
        "también", "sobre", "parte", "cada", "otro", "puede", "tiene",
        "tiempo", "mismo", "mayor", "donde", "antes", "porque",
        "nunca", "desde", "hasta", "ella", "este", "algo", "nada",
        "tanto", "siempre", "años", "forma", "hacer", "solo", "sólo",
        "cosa", "cosas", "mundo", "largo", "quien", "quienes",
        "durante", "mientras",
    ],
    "pt": [
        "que", "para", "com", "por", "mais", "como", "dos", "das",
        "mas", "mas", "são", "entre", "tambem", "também", "sobre",
        "pode", "cada", "outro", "ainda", "depois", "antes", "muito",
        "grande", "tempo", "lugar", "coisa", "todas", "todos",
        "geral", "através", "durante", "enquanto", "assim", "parte",
        "depois", "primeiro", "outra", "mundo", "vida", "caso",
        "agora", "estar", "tinha", "seria", "nosso", "coisas",
    ],
}

# 降低非英语高频词权重，排除与英语共有的常见词
_ENGLISH_ONLY_WORDS: List[str] = [
    "the", "and", "you", "not", "but", "for", "all", "are",
    "can", "has", "had", "her", "was", "our", "out", "one",
    "some", "them", "than", "that", "this", "what", "when",
    "where", "which", "while", "will", "with", "would", "your",
    "their", "there", "these", "they", "think", "those", "under",
    "after", "because", "before", "being", "between", "does",
    "every", "going", "just", "know", "like", "made", "make",
    "more", "most", "much", "must", "need", "never", "only",
    "other", "over", "own", "people", "place", "right", "said",
    "same", "still", "such", "take", "tell", "thing", "time",
    "too", "two", "way", "year", "years",
]


def _detect_european_lang(text_lower: str) -> Optional[str]:
    """使用高频词检测欧洲语言。"""
    words = set(re.findall(r"[a-zà-ÿ]+", text_lower))

    # 统计各语言的高频词匹配数
    scores: Dict[str, int] = {}
    for lang, common_words in _LANG_COMMON_WORDS.items():
        # 只统计数据集中定义的词
        scores[lang] = sum(1 for w in common_words if w in words)

    if not scores or max(scores.values()) == 0:
        return None

    # 如果有明确的高频词优势且超过 2 分，判定为该语言
    sorted_langs = sorted(scores.items(), key=lambda x: -x[1])
    top_lang, top_score = sorted_langs[0]

    if top_score >= 3:
        # 检查是否可能实际上是英语
        if top_lang != "en":
            english_words = sum(
                1 for w in _ENGLISH_ONLY_WORDS if w in words
            )
            if english_words >= top_score:
                return "en"

        return top_lang

    return None


# ---------------------------------------------------------------------------
# 主要检测函数
# ---------------------------------------------------------------------------


# 检测结果类型
DetectResult = Tuple[str, float]  # (language_code, confidence)


def detect_language(text: str) -> DetectResult:
    """检测文本的语言。

    使用 Unicode 字符范围检测 CJK/日语/韩语/阿拉伯语/泰语/西里尔语，
    使用高频词典区分欧洲语言。

    Args:
        text: 待检测文本（至少应有几个非空白字符）。

    Returns:
        DetectResult: (语言代码, 置信度 0.0-1.0)。
    """
    text = text.strip()
    if not text:
        return ("en", 0.0)

    # 去除非内容字符以统计有效字符
    content_chars = [ch for ch in text if not ch.isspace()]
    total = len(content_chars)
    if total == 0:
        return ("en", 0.0)

    # 统计各脚本的字符数
    cjk = _has_cjk(text)
    hira = _has_hiragana(text)
    kata = _has_katakana(text)
    hangul = _has_hangul(text)
    arabic = _has_arabic(text)
    thai = _has_thai(text)
    cyrillic = _has_cyrillic(text)
    latin_ext = _has_latin_ext(text)

    # 基础 ASCII 字母
    ascii_letters = sum(1 for ch in content_chars if "a" <= ch <= "z" or "A" <= ch <= "Z")

    # --- 非拉丁脚本检测 ---

    # 日语：有平假名或少量汉字+片假名
    if hira > 0 or kata > 0:
        ratio = (hira + kata) / max(total, 1)
        if ratio > 0.1:
            return ("ja", min(ratio + 0.2, 0.98))
        # 日语中可能有大量汉字 + 少量假名
        if cjk > 0 and (hira + kata) >= 2:
            return ("ja", 0.85)

    # 韩语：有谚文音节
    if hangul > 0:
        ratio = hangul / max(total, 1)
        return ("ko", min(ratio + 0.15, 0.98))

    # 阿拉伯语
    if arabic > 0:
        ratio = arabic / max(total, 1)
        return ("ar", min(ratio + 0.15, 0.98))

    # 泰语
    if thai > 0:
        ratio = thai / max(total, 1)
        return ("th", min(ratio + 0.15, 0.98))

    # 中文：只有 CJK，无假名
    if cjk > 0 and hira == 0 and kata == 0:
        ratio = cjk / max(total, 1)
        return ("zh", min(ratio + 0.15, 0.98))

    # 西里尔字母（俄语等）
    if cyrillic > 0:
        ratio = cyrillic / max(total, 1)
        # 可以与 ascii 混合（科技文本），但如果西里尔占主导，判定为 ru
        if ratio > 0.3:
            return ("ru", min(ratio + 0.1, 0.95))

    # --- 拉丁字母语言检测 ---

    # 如果主要是 ASCII 字母或扩展拉丁文，使用高频词检测
    latin_total = ascii_letters + latin_ext
    if latin_total > 0 and latin_total / max(total, 1) > 0.3:
        text_lower = text.lower()
        result = _detect_european_lang(text_lower)
        if result:
            return (result, 0.75)

        # 默认：如果只有 ASCII 字母且无扩展拉丁符，判为英语
        if latin_ext == 0 and ascii_letters > 0:
            return ("en", 0.5)

        # 有扩展拉丁符（如 é, ñ, ü）但仍无法确定
        if latin_ext > 0:
            return ("en", 0.4)

    # 兜底
    return ("en", 0.3)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI 入口: python -m core.lang_detector"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python -m core.lang_detector <文本>")
        sys.exit(1)

    text = " ".join(sys.argv[1:])
    lang, confidence = detect_language(text)
    print(f"语言: {lang}  (置信度: {confidence:.2f})")


if __name__ == "__main__":
    main()