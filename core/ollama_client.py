"""Ollama REST API 客户端。

封装 Ollama API 为类型安全的 Python 接口，支持同步/流式调用。
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

import httpx


class OllamaError(Exception):
    """Ollama API 调用基础异常。"""


class OllamaConnectionError(OllamaError):
    """无法连接 Ollama 服务。"""


class OllamaModelNotFoundError(OllamaError):
    """模型未找到或未下载。"""


class OllamaTimeoutError(OllamaError):
    """请求超时。"""


class OllamaResponseError(OllamaError):
    """API 返回错误响应。"""


@dataclass(frozen=True)
class ModelInfo:
    """已下载模型信息。"""

    name: str
    size: int
    digest: str
    modified_at: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerateResponse:
    """翻译/生成响应。"""

    model: str
    response: str
    done: bool
    total_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    eval_count: Optional[int] = None


DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0


class OllamaClient:
    """Ollama REST API 客户端。

    用法:
        client = OllamaClient()
        models = client.list_models()
        result = client.generate("translategemma:4b", "Translate: hello")
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout),
            headers={"Content-Type": "application/json"},
        )

    def _check_connection(self) -> None:
        """检查 Ollama 服务是否可达。"""
        try:
            resp = self._client.get("/api/tags", timeout=5.0)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                f"无法连接 Ollama 服务 ({self._base_url})。"
                f"请确认 Ollama 已启动: {exc}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError(
                "连接 Ollama 服务超时 (5s)"
            ) from exc

    def list_models(self) -> List[ModelInfo]:
        """获取已下载模型列表。

        Returns:
            List[ModelInfo]: 模型信息列表。

        Raises:
            OllamaConnectionError: 无法连接服务。
        """
        try:
            resp = self._client.get("/api/tags", timeout=10.0)
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                f"无法连接 Ollama 服务 ({self._base_url})"
            ) from exc
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("请求模型列表超时") from exc

        data = resp.json()
        models: List[ModelInfo] = []
        for m in data.get("models", []):
            models.append(
                ModelInfo(
                    name=m["name"],
                    size=m.get("size", 0),
                    digest=m.get("digest", ""),
                    modified_at=m.get("modified_at", ""),
                    details=m.get("details", {}),
                )
            )
        models.sort(key=lambda x: x.name)
        return models

    def generate(
        self,
        model: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_length: int = 2048,
        stream: bool = False,
        keep_alive: int = -1,
    ) -> GenerateResponse:
        """同步生成/翻译调用。

        Args:
            model: 模型名称。
            prompt: 输入提示词。
            temperature: 温度参数，翻译用 0.0。
            max_length: 最大生成长度。
            stream: 是否流式输出。
            keep_alive: 模型保持加载时间，-1 表示永久。

        Returns:
            GenerateResponse: 生成结果。

        Raises:
            OllamaConnectionError: 无法连接。
            OllamaModelNotFoundError: 模型不存在。
            OllamaTimeoutError: 超时。
            OllamaResponseError: API 错误。
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_length,
            },
            "keep_alive": keep_alive,
        }

        last_error: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self._client.post(
                    "/api/generate",
                    json=payload,
                    timeout=self._timeout,
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 404:
                    raise OllamaModelNotFoundError(
                        f"模型 '{model}' 未找到。请先下载: ollama pull {model}"
                    ) from exc
                raise OllamaResponseError(
                    f"API 返回错误 ({status}): {exc.response.text}"
                ) from exc
            except httpx.ConnectError as exc:
                raise OllamaConnectionError(
                    f"无法连接 Ollama 服务 ({self._base_url})"
                ) from exc
            except httpx.TimeoutException as exc:
                last_error = OllamaTimeoutError(
                    f"请求超时 ({self._timeout}s)，"
                    f"尝试 {attempt}/{MAX_RETRIES}"
                )
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF * attempt)
                continue

            data = resp.json()
            return GenerateResponse(
                model=data.get("model", model),
                response=data.get("response", "").strip(),
                done=data.get("done", True),
                total_duration=data.get("total_duration"),
                prompt_eval_count=data.get("prompt_eval_count"),
                eval_count=data.get("eval_count"),
            )

        raise OllamaTimeoutError(
            f"请求在 {MAX_RETRIES} 次重试后仍超时"
        ) from last_error

    def generate_stream(
        self,
        model: str,
        prompt: str,
        *,
        temperature: float = 0.0,
        max_length: int = 2048,
        keep_alive: int = -1,
    ) -> Iterator[str]:
        """流式生成/翻译调用。

        以生成器方式逐块返回翻译文本。

        Args:
            model: 模型名称。
            prompt: 输入提示词。
            temperature: 温度参数。
            max_length: 最大生成长度。
            keep_alive: 模型保持加载时间。

        Yields:
            str: 每次输出的文本片段。

        Raises:
            OllamaConnectionError: 无法连接。
            OllamaModelNotFoundError: 模型不存在。
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_length,
            },
            "keep_alive": keep_alive,
        }

        try:
            with self._client.stream(
                "POST",
                "/api/generate",
                json=payload,
                timeout=self._timeout,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    if chunk:
                        yield chunk
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise OllamaModelNotFoundError(
                    f"模型 '{model}' 未找到。请先下载: ollama pull {model}"
                ) from exc
            raise OllamaResponseError(
                f"API 返回错误: {exc.response.text}"
            ) from exc
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                f"无法连接 Ollama 服务 ({self._base_url})"
            ) from exc

    def stop_model(self, model: str) -> None:
        """卸载指定模型。

        Args:
            model: 模型名称。

        Raises:
            OllamaConnectionError: 无法连接。
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": "",
            "keep_alive": 0,
        }
        try:
            resp = self._client.post(
                "/api/generate", json=payload, timeout=10.0
            )
            resp.raise_for_status()
        except httpx.ConnectError as exc:
            raise OllamaConnectionError(
                f"无法连接 Ollama 服务 ({self._base_url})"
            ) from exc

    def close(self) -> None:
        """关闭 HTTP 客户端。"""
        self._client.close()


def _format_size(size: int) -> str:
    """格式化文件大小。"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024**2:
        return f"{size/1024:.1f} KB"
    elif size < 1024**3:
        return f"{size/1024**2:.1f} MB"
    else:
        return f"{size/1024**3:.2f} GB"


def main() -> None:
    """CLI 入口: python -m core.ollama_client <subcommand>"""
    import argparse

    parser = argparse.ArgumentParser(prog="ollama_client")
    sub = parser.add_subparsers(dest="cmd")

    list_parser = sub.add_parser("list", help="列出已下载模型")
    list_parser.add_argument("--json", action="store_true", help="JSON 格式输出")

    gen_parser = sub.add_parser("generate", help="调用翻译")
    gen_parser.add_argument("model", help="模型名称")
    gen_parser.add_argument("text", help="待翻译文本")
    gen_parser.add_argument(
        "--source", "-s", default="en", help="源语言"
    )
    gen_parser.add_argument(
        "--target", "-t", default="zh", help="目标语言"
    )
    gen_parser.add_argument(
        "--stream", action="store_true", help="流式输出"
    )
    gen_parser.add_argument(
        "--temperature", type=float, default=0.0, help="温度参数"
    )

    stop_parser = sub.add_parser("stop", help="卸载模型")
    stop_parser.add_argument("model", help="模型名称")

    args = parser.parse_args()

    if not args.cmd:
        parser.print_help()
        sys.exit(1)

    client = OllamaClient()

    try:
        if args.cmd == "list":
            models = client.list_models()
            if args.json:
                output = []
                for m in models:
                    output.append(
                        {
                            "name": m.name,
                            "size": _format_size(m.size),
                            "modified": m.modified_at,
                        }
                    )
                print(json.dumps(output, ensure_ascii=False, indent=2))
            else:
                if not models:
                    print("没有已下载的模型。")
                    print("使用 ollama pull <model> 下载模型。")
                    return
                print(f"已下载 {len(models)} 个模型:\n")
                for m in models:
                    size_str = _format_size(m.size)
                    print(f"  {m.name:<40s} {size_str:>10s}")

        elif args.cmd == "generate":
            prompt = (
                f"Translate the following {args.source} text "
                f"to {args.target}: {args.text}"
            )
            if args.stream:
                print(f"[流式] {args.model} ...")
                for chunk in client.generate_stream(
                    args.model, prompt, temperature=args.temperature
                ):
                    print(chunk, end="", flush=True)
                print()
            else:
                result = client.generate(
                    args.model, prompt, temperature=args.temperature
                )
                print(result.response)

        elif args.cmd == "stop":
            client.stop_model(args.model)
            print(f"模型 '{args.model}' 已卸载。")

    except OllamaError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
