"""入口：python -m InvoiceApp 启动"""

import os
import sys

# 确保项目根目录在路径中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from InvoiceApp.ui.main_window import MainWindow  # noqa: E402
from InvoiceApp.ui.resources import load_style  # noqa: E402


def main():
    # 高DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName('InvoiceApp')
    app.setOrganizationName('InvoiceApp')

    # 加载样式
    load_style(app)

    # 启动主窗口
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
