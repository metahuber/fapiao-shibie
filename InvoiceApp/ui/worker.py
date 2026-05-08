"""后台工作线程（并行扫描 PDF）"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QThread, Signal

# 并行工作线程数（I/O 密集型，4 路可充分利用磁盘读取带宽）
_MAX_WORKERS = 4


class ScanWorker(QThread):
    """后台扫描 PDF 的工作线程（并行）"""

    progress = Signal(int, int, str, dict)  # current, total, filename, data_dict
    finished = Signal(list)  # results [(data_dict, path), ...]

    def __init__(self, pdf_files, parent=None):
        super().__init__(parent)
        self.pdf_files = pdf_files

    def run(self):
        """在后台线程中运行"""
        from ..core.parser import process_pdf

        total = len(self.pdf_files)
        if total == 0:
            self.finished.emit([])
            return

        results: dict[int, tuple] = {}

        with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, total)) as executor:
            # 提交所有任务，保留索引以恢复原始顺序
            future_map = {
                executor.submit(process_pdf, path): (i, path)
                for i, path in enumerate(self.pdf_files)
            }

            completed = 0
            for future in as_completed(future_map):
                if self.isInterruptionRequested():
                    # 取消未启动的任务
                    for f in future_map:
                        f.cancel()
                    break

                i, path = future_map[future]
                try:
                    data, _ = future.result()
                    results[i] = (data, path)
                except Exception as e:
                    data = {'error': str(e)}
                    results[i] = (data, path)

                completed += 1
                self.progress.emit(completed, total, path, data)

        # 按原始文件顺序输出
        ordered = [results[i] for i in range(total) if i in results]
        self.finished.emit(ordered)
