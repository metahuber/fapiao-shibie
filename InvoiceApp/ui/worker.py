"""后台工作线程"""

from PySide6.QtCore import QThread, Signal


class ScanWorker(QThread):
    """后台扫描 PDF 的工作线程"""

    progress = Signal(int, int, str)  # current, total, filename
    finished = Signal(list)           # results
    error = Signal(str)               # error message

    def __init__(self, pdf_files, parent=None):
        super().__init__(parent)
        self.pdf_files = pdf_files

    def run(self):
        """在后台线程中运行"""
        from ..core.parser import process_pdf

        results = []
        total = len(self.pdf_files)

        for i, pdf_path in enumerate(self.pdf_files):
            if self.isInterruptionRequested():
                break

            data, path = process_pdf(pdf_path)
            results.append((data, path))

            self.progress.emit(i + 1, total, path)

        self.finished.emit(results)
