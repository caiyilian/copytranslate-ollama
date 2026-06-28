"""翻译工作线程。

在 QThread 中运行 translate_once，通过信号槽安全地将进度和结果传回主线程。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from core.pipeline import Pipeline


class TranslateWorker(QObject):
    """翻译工作线程对象。

    用法:
        worker = TranslateWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(lambda: worker.run(text, "en", "zh", "model"))
        worker.finished.connect(thread.quit)
        thread.start()
    """

    progress = pyqtSignal(int, int)   # current, total
    finished = pyqtSignal(str, str)   # result, detected
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self, pipeline: Optional[Pipeline] = None) -> None:
        super().__init__()
        self._pipeline = pipeline or Pipeline()

    def run(
        self,
        text: str,
        source: str,
        target: str,
        model: str,
        temperature: float = 0.0,
        max_length: int = 2048,
    ) -> None:
        """在工作线程中执行翻译。"""
        try:
            result, detected = self._pipeline.translate_once(
                text=text,
                source=source,
                target=target,
                model=model,
                temperature=temperature,
                max_length=max_length,
                progress_callback=lambda c, t: self.progress.emit(c, t),
            )
            self.finished.emit(result, detected)
        except Exception as e:
            self.error_occurred.emit(str(e))