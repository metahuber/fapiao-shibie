"""PDF 页面预览 — 可选依赖 PyMuPDF，缺失时静默降级"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QLabel, QScrollArea, QVBoxLayout

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


class PdfPreviewDialog(QDialog):
    """PDF 放大预览弹窗，支持鼠标滚轮缩放"""

    def __init__(self, pdf_path: str, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self._scale = 1.0
        self.setWindowTitle('发票预览')
        self.setMinimumSize(700, 800)
        self.resize(800, 900)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet('background-color: #f0f0f0;')

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet('background-color: white;')

        scroll.setWidget(self._image_label)
        layout.addWidget(scroll)

        self._render()

    def _render(self):
        pix = get_page_pixmap(self.pdf_path, self._scale)
        if pix and not pix.isNull():
            self._image_label.setPixmap(pix)
            self._image_label.resize(pix.size())

    def wheelEvent(self, event):
        """滚轮缩放"""
        delta = event.angleDelta().y()
        if delta > 0:
            self._scale = min(self._scale * 1.15, 3.0)
        else:
            self._scale = max(self._scale / 1.15, 0.2)
        self._render()


class PdfPreviewLabel(QLabel):
    """PDF 预览标签，点击可放大查看"""

    previewClicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pdf_path = ''
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(120)
        self.setMaximumHeight(280)
        self.setStyleSheet(
            'background-color: #f5f5f5; border-radius: 6px;'
            ' border: 1px solid #e0e0e0; padding: 4px;'
        )
        self.setCursor(Qt.PointingHandCursor)
        if not _HAS_PDF_PREVIEW:
            self.hide()

    def mousePressEvent(self, event):
        if self._pdf_path:
            dlg = PdfPreviewDialog(self._pdf_path, self.window())
            dlg.exec()
        super().mousePressEvent(event)

    def show_preview(self, pdf_path: str):
        """显示 PDF 第一页预览"""
        self._pdf_path = pdf_path
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
        self._pdf_path = ''
        self.clear()
        self.hide()
