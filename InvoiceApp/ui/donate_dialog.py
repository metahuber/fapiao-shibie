"""打赏对话框"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DonateDialog(QDialog):
    """显示打赏收款码"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('支持作者')
        self.setFixedSize(520, 320)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title = QLabel('如果这个工具对你有帮助，欢迎打赏支持作者')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('font-size: 14px; font-weight: bold; color: #212121; margin: 8px;')
        layout.addWidget(title)

        # 并排显示两个码
        cards = QHBoxLayout()
        cards.setSpacing(16)

        res_dir = Path(__file__).resolve().parent.parent / 'resources'

        for name, label, fname in [
            ('wechat', '微信收款码', 'weixin_shoukuan.jpg'),
            ('alipay', '支付宝收款码', 'zhifubao_shoukuan.jpg'),
        ]:
            card = QWidget()
            card.setFixedWidth(220)
            card_layout = QVBoxLayout(card)
            card_layout.setAlignment(Qt.AlignCenter)

            img_path = res_dir / fname
            if img_path.exists():
                pix = QPixmap(str(img_path))
                pix = pix.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label = QLabel()
                img_label.setPixmap(pix)
                img_label.setAlignment(Qt.AlignCenter)
                card_layout.addWidget(img_label)

            name_label = QLabel(label)
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet('color: #757575; font-size: 12px; margin-top: 4px;')
            card_layout.addWidget(name_label)

            cards.addWidget(card)

        layout.addLayout(cards)

        # 关闭按钮
        btn_close = QPushButton('关闭')
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
