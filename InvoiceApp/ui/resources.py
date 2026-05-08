"""UI 资源模块 - 图标和样式"""

from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QSize
from PySide6.QtSvg import QSvgRenderer


def load_style(app):
    """加载 QSS 样式表"""
    qss_path = Path(__file__).parent.parent / 'resources' / 'style.qss'
    if qss_path.exists():
        with open(qss_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())


def _make_icon(svg_content, size=24):
    """从 SVG 字符串生成 QIcon"""
    renderer = QSvgRenderer(svg_content.encode('utf-8'))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def get_icons():
    """获取所有工具图标"""
    return {
        'folder': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#616161">
                <path d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z"/>
            </svg>"""),
        'play': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ffffff">
                <path d="M8 5v14l11-7z"/>
            </svg>"""),
        'export': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ffffff">
                <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/>
            </svg>"""),
        'clear': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#616161">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>"""),
        'success': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#4caf50">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>"""),
        'error': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#f44336">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
            </svg>"""),
        'info': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#1976d2">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
            </svg>"""),
        'settings': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#616161">
                <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.07.62-.07.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
            </svg>"""),
        'about': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#616161">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
            </svg>"""),
        'app': _make_icon("""
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#1976d2">
                <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
            </svg>"""),
    }
