"""导出字段选择对话框"""

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..core.parser import MERGE_FIELDS


class FieldSelectDialog(QDialog):
    """选择导出哪些字段"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('选择导出字段')
        self.setMinimumWidth(400)
        self._checkboxes: list[QCheckBox] = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        layout.addWidget(QLabel('导出字段（每张发票一行，项目明细合并）'))
        for display_name, key in MERGE_FIELDS:
            cb = QCheckBox(display_name)
            cb.setChecked(True)
            cb.key = key
            self._checkboxes.append(cb)
            layout.addWidget(cb)

        # 全选/取消
        btn_layout = QHBoxLayout()
        btn_all = QPushButton('全选')
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton('取消全选')
        btn_none.clicked.connect(lambda: self._set_all(False))
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 确定/取消
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_all(self, checked: bool):
        for cb in self._checkboxes:
            cb.setChecked(checked)

    def selected_fields(self) -> list:
        """返回选中的字段列表 [(显示名, 键名), ...]"""
        result = []
        for cb in self._checkboxes:
            if cb.isChecked():
                display = cb.text()
                key = cb.key
                result.append((display, key))
        return result
