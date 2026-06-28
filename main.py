"""CopyTranslator-Ollama — 本地翻译助手入口。

基于 Ollama 专用翻译模型的纯离线剪贴板翻译工具。

用法:
    python main.py --version    # 查看版本
    python main.py --help       # 查看帮助
    python main.py listen       # 启动剪贴板监听模式
    python main.py gui          # 启动 GUI 模式
"""

from __future__ import annotations

import argparse
import sys

VERSION = "0.1.0"
PROJECT = "CopyTranslator-Ollama"


def cmd_version() -> None:
    """输出版本信息。"""
    print(f"{PROJECT} v{VERSION}")


def cmd_listen(args: argparse.Namespace) -> None:
    """启动剪贴板监听模式。"""
    from core.pipeline import Pipeline

    pipeline = Pipeline()
    try:
        pipeline.run_listen(
            model=args.model,
            source=args.source or "auto",
            target=args.target or "zh",
        )
    finally:
        pipeline.close()


def cmd_gui(args: argparse.Namespace) -> None:
    """启动 GUI 模式。"""
    from ui.main_window import MainWindow

    window = MainWindow(mode=args.mode or "contrast")
    window.run()


def build_parser() -> argparse.ArgumentParser:
    """构建参数解析器。"""
    parser = argparse.ArgumentParser(
        prog=PROJECT,
        description="基于 Ollama 专用翻译模型的纯离线剪贴板翻译工具",
        epilog="更多信息: https://github.com/caiyilian/copytranslate-ollama",
    )
    parser.add_argument(
        "--version",
        "-V",
        action="store_true",
        help="输出版本号并退出",
    )

    sub = parser.add_subparsers(title="子命令", dest="command")

    listen_parser = sub.add_parser(
        "listen",
        help="启动剪贴板监听模式",
        description="监听系统剪贴板变化，自动翻译并显示结果",
    )
    listen_parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="指定翻译模型（覆盖配置文件中的设置）",
    )
    listen_parser.add_argument(
        "--source",
        "-s",
        default=None,
        help="源语言代码（如 en, auto）",
    )
    listen_parser.add_argument(
        "--target",
        "-t",
        default=None,
        help="目标语言代码（如 zh）",
    )

    gui_parser = sub.add_parser(
        "gui",
        help="启动 GUI 模式",
        description="打开图形用户界面",
    )
    gui_parser.add_argument(
        "--mode",
        choices=["contrast", "focus"],
        default=None,
        help="启动时默认显示模式",
    )

    return parser


def main() -> None:
    """主入口。"""
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        cmd_version()
        sys.exit(0)

    if args.command == "listen":
        cmd_listen(args)
    elif args.command == "gui":
        cmd_gui(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
