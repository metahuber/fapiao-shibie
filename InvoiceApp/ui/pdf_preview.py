"""PDF 页面预览 — 可选依赖 PyMuPDF，缺失时静默降级"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

try:
    import fitz  # PyMuPDF

    _HAS_PDF_PREVIEW = True
except ImportError:
    _HAS_PDF_PREVIEW = False


def has_preview() -> bool:
    """PyMuPDF 是否可用"""
    return _HAS_PDF_PREVIEW


def get_page_pixmap(pdf_path: str, scale: float = 0.3) -> QPixmap | None:
    """渲染 PDF 第一页为 QPixmap"""
    if not _HAS_PDF_PREVIEW:
        return None
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        mat = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=mat)
        img = QPixmap()
        img.loadFromData(pix.tobytes('png'))
        doc.close()
        return img
    except Exception:
        return None


class PdfPreviewLabel(QLabel):
    """PDF 预览标签，可选显示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(120)
        self.setMaximumHeight(280)
        self.setStyleSheet(
            'background-color: #f5f5f5; border-radius: 6px;'
            ' border: 1px solid #e0e0e0; padding: 4px;'
        )
        if not _HAS_PDF_PREVIEW:
            self.hide()

    def show_preview(self, pdf_path: str):
        """显示 PDF 第一页预览"""
        if not _HAS_PDF_PREVIEW:
            self.hide()
            return
        pix = get_page_pixmap(pdf_path)
        if pix and not pix.isNull():
            self.setPixmap(pix)
            self.show()
        else:
            self.hide()

    def clear_preview(self):
        """清除预览"""
        self.clear()
        self.hide()
