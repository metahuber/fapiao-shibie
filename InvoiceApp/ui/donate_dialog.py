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

    _CARD_STYLE = (
        'background-color: #ffffff; border: 1px solid #e0e0e0;'
        ' border-radius: 8px; padding: 8px;'
    )
    _TITLE_STYLE = (
        'font-size: 14px; font-weight: bold; color: #212121; margin: 4px 0;'
    )
    _SUBTITLE_STYLE = (
        'font-size: 12px; color: #757575; margin: 0 0 8px 0;'
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('支持作者')
        self.setFixedSize(540, 380)
        self.setStyleSheet('background-color: #f5f6fa;')
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(24, 20, 24, 16)

        # 客气话
        title = QLabel('感谢您使用本工具 ❤')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(self._TITLE_STYLE)
        layout.addWidget(title)

        subtitle = QLabel(
            '如果您觉得工具好用，欢迎打赏支持作者持续开发'
        )
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet(self._SUBTITLE_STYLE)
        layout.addWidget(subtitle)

        # 两个收款码
        cards = QHBoxLayout()
        cards.setSpacing(20)
        cards.setContentsMargins(0, 8, 0, 0)

        res_dir = Path(__file__).resolve().parent.parent / 'resources'

        for label, fname in [
            ('微信收款码', 'weixin_shoukuan.png'),
            ('支付宝收款码', 'zhifubao_shoukuan.png'),
        ]:
            card = QWidget()
            card.setFixedSize(220, 260)
            card.setStyleSheet(self._CARD_STYLE)
            card_layout = QVBoxLayout(card)
            card_layout.setAlignment(Qt.AlignCenter)
            card_layout.setContentsMargins(8, 8, 8, 8)

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
            name_label.setStyleSheet(
                'color: #9e9e9e; font-size: 12px; border: none;'
            )
            card_layout.addWidget(name_label)

            cards.addWidget(card)

        layout.addLayout(cards)
        layout.addStretch()

        # 关闭按钮
        btn_close = QPushButton('关闭')
        btn_close.setFixedWidth(100)
        btn_close.setStyleSheet(
            'background-color: #1976d2; color: #ffffff;'
            ' border: none; border-radius: 6px; padding: 8px 16px;'
            ' font-weight: bold;'
        )
        btn_close.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
