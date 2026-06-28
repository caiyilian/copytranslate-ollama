#!/usr/bin/env python
"""CopyTranslator-Ollama PyQt6 入口。"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from ui_qt.main_window import MainWindow


def main() -> None:
    """启动 PyQt6 界面。"""
    app = QApplication(sys.argv)
    app.setApplicationName("CopyTranslator-Ollama")
    app.setOrganizationName("caiyilian")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()