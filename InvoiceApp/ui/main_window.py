"""主窗口"""

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QSettings,
    QSize,
    QSortFilterProxyModel,
    Qt,
    QTimer,
    QUrl,
    Slot,
)
from PySide6.QtGui import QAction, QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableView,
    QTextBrowser,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.exporter import export_to_csv, export_to_excel
from ..core.parser import (
    BASIC_FIELDS,
    ITEM_FIELDS,
    flatten_results,
    scan_pdf_files_recursive,
)
from .pdf_preview import PdfPreviewLabel
from .resources import get_icons
from .worker import ScanWorker


class InvoiceTableModel(QAbstractTableModel):
    """发票数据表格模型"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = []  # [(data_dict, pdf_path), ...]
        # 表格显示的关键字段
        self._display_fields = [
            ('文件名', '文件名'),
            ('发票号码', '发票号码'),
            ('开票日期', '开票日期'),
            ('购买方名称', '购买方名称'),
            ('销售方名称', '销售方名称'),
            ('价税合计', '价税合计'),
            ('开票人', '开票人'),
        ]

    @property
    def column_count(self):
        return len(self._display_fields)

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return self.column_count

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._data):
            return None
        data_dict, _ = self._data[index.row()]
        _, key = self._display_fields[index.column()]

        if role == Qt.DisplayRole:
            value = data_dict.get(key, '')
            # 格式化价税合计显示
            if key == '价税合计' and isinstance(value, (int, float)):
                return f'¥{value:.2f}'
            return str(value) if value is not None else ''

        if role == Qt.TextAlignmentRole:
            if key in ('价税合计', '数量', '单价', '金额'):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        if role == Qt.ToolTipRole:
            value = data_dict.get(key, '')
            return str(value) if value else None

        if role == Qt.BackgroundRole and index.column() == 0:
            if 'error' in data_dict:
                return QColor(255, 235, 238)  # 淡红背景
            return QColor(232, 245, 233)  # 淡绿背景

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < self.column_count:
                return self._display_fields[section][0]
        return None

    def set_results(self, results):
        self.beginResetModel()
        self._data = results
        self.endResetModel()

    def get_result(self, row):
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def get_all_results(self):
        return self._data

    def get_error_count(self):
        return sum(1 for d, _ in self._data if 'error' in d)

    def get_total_amount(self):
        total = 0
        for d, _ in self._data:
            val = d.get('价税合计')
            if isinstance(val, (int, float)):
                total += val
        return total


class InvoiceFilterProxy(QSortFilterProxyModel):
    """跨所有可见列进行不区分大小写的文本搜索"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_text = ''

    def set_filter_text(self, text):
        self._filter_text = text
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._filter_text:
            return True
        needle = self._filter_text.lower()
        model = self.sourceModel()
        if model is None:
            return True
        for col in range(model.columnCount()):
            idx = model.index(source_row, col, source_parent)
            data = model.data(idx, Qt.DisplayRole)
            if data and needle in str(data).lower():
                return True
        return False


class StatsWidget(QFrame):
    """统计信息面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('statsWidget')
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 总文件数
        self.lbl_total_label = QLabel('PDF文件')
        self.lbl_total_label.setStyleSheet('color: #757575; font-size: 11px;')
        self.lbl_total_value = QLabel('0')
        self.lbl_total_value.setProperty('statValue', True)
        self.lbl_total_value.setStyleSheet('color: #1976d2; font-size: 18px; font-weight: bold;')

        # 成功数
        self.lbl_ok_label = QLabel('识别成功')
        self.lbl_ok_label.setStyleSheet('color: #757575; font-size: 11px;')
        self.lbl_ok_value = QLabel('0')
        self.lbl_ok_value.setProperty('statValue', True)
        self.lbl_ok_value.setStyleSheet('color: #2e7d32; font-size: 18px; font-weight: bold;')

        # 失败数
        self.lbl_fail_label = QLabel('识别失败')
        self.lbl_fail_label.setStyleSheet('color: #757575; font-size: 11px;')
        self.lbl_fail_value = QLabel('0')
        self.lbl_fail_value.setProperty('statValue', True)
        self.lbl_fail_value.setStyleSheet('color: #c62828; font-size: 18px; font-weight: bold;')

        # 金额合计
        self.lbl_amount_label = QLabel('金额合计')
        self.lbl_amount_label.setStyleSheet('color: #757575; font-size: 11px;')
        self.lbl_amount_value = QLabel('¥0.00')
        self.lbl_amount_value.setProperty('statValue', True)
        self.lbl_amount_value.setStyleSheet('color: #e65100; font-size: 18px; font-weight: bold;')

        # 使用分割线
        def add_stat(layout, label_w, value_w):
            vbox = QVBoxLayout()
            vbox.setSpacing(0)
            vbox.addWidget(value_w, 0, Qt.AlignCenter)
            vbox.addWidget(label_w, 0, Qt.AlignCenter)
            layout.addLayout(vbox)

        add_stat(layout, self.lbl_total_label, self.lbl_total_value)
        layout.addWidget(self._separator())
        add_stat(layout, self.lbl_ok_label, self.lbl_ok_value)
        layout.addWidget(self._separator())
        add_stat(layout, self.lbl_fail_label, self.lbl_fail_value)
        layout.addWidget(self._separator())
        add_stat(layout, self.lbl_amount_label, self.lbl_amount_value)
        layout.addStretch()

    def _separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet('color: #e0e0e0;')
        sep.setFixedWidth(1)
        return sep

    def update_stats(self, total, success, failed, amount):
        self.lbl_total_value.setText(str(total))
        self.lbl_ok_value.setText(str(success))
        self.lbl_fail_value.setText(str(failed))
        self.lbl_amount_value.setText(f'¥{amount:.2f}')


class MainWindow(QMainWindow):
    """应用主窗口"""

    def __init__(self):
        super().__init__()
        self.icons = get_icons()
        self.settings = QSettings('InvoiceApp', 'InvoiceApp')
        self.worker = None
        self.results = []  # [(data_dict, pdf_path), ...]

        self.setup_window()
        self.create_menu_bar()
        self.create_toolbar()
        self.create_central_widget()
        self.create_status_bar()
        self.connect_signals()
        self.restore_settings()

    def setup_window(self):
        self.setWindowTitle('数电发票识别工具')
        self.setWindowIcon(self.icons['app'])
        self.resize(1100, 720)

    # ---- 菜单栏 ----

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        # 文件菜单
        file_menu = menu_bar.addMenu('文件(&F)')

        act_browse = QAction('选择文件夹(&O)', self, shortcut='Ctrl+O')
        act_browse.triggered.connect(self.browse_folder)
        file_menu.addAction(act_browse)
        file_menu.addSeparator()

        self.recent_menu = file_menu.addMenu('最近文件夹')
        self._update_recent_menu()
        file_menu.addSeparator()

        act_exit = QAction('退出(&X)', self, shortcut='Alt+F4')
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # 视图菜单
        view_menu = menu_bar.addMenu('视图(&V)')
        self.act_clear = QAction('清空结果', self, shortcut='Ctrl+L')
        self.act_clear.setEnabled(False)
        self.act_clear.triggered.connect(self.clear_results)
        view_menu.addAction(self.act_clear)

        # 帮助菜单
        help_menu = menu_bar.addMenu('帮助(&H)')
        act_about = QAction('关于', self)
        act_about.triggered.connect(self.show_about)
        help_menu.addAction(act_about)

        # 键盘快捷键
        self.act_start = QAction('开始识别', self, shortcut='Ctrl+R')
        self.act_start.setEnabled(False)
        self.act_start.triggered.connect(self.start_scan)
        self.act_export = QAction('导出数据', self, shortcut='Ctrl+E')
        self.act_export.setEnabled(False)
        self.act_export.triggered.connect(self.export_data)

    # ---- 工具栏 ----

    def create_toolbar(self):
        toolbar = QToolBar('主工具栏')
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        self.addToolBar(toolbar)

        self.tbtn_browse = toolbar.addAction(self.icons['folder'], '选择文件夹')
        self.tbtn_browse.triggered.connect(self.browse_folder)

        toolbar.addSeparator()

        # 开始识别按钮 — 用文本，不用图标（避免渲染兼容问题）
        self.tbtn_start = QPushButton('▶ 开始识别')
        self.tbtn_start.setObjectName('btnStart')
        self.tbtn_start.setFixedHeight(34)
        self.tbtn_start.clicked.connect(self.start_scan)
        self.tbtn_start.setEnabled(False)
        self.act_start.setEnabled(False)
        toolbar.addWidget(self.tbtn_start)

        toolbar.addSeparator()

        # 导出Excel按钮 — 用文本
        self.tbtn_export = QPushButton('📤 导出')
        self.tbtn_export.setObjectName('btnExport')
        self.tbtn_export.setFixedHeight(34)
        self.tbtn_export.clicked.connect(self.export_data)
        self.tbtn_export.setEnabled(False)
        toolbar.addWidget(self.tbtn_export)

        toolbar.addSeparator()

        self.tbtn_clear = QPushButton('✕ 清空')
        self.tbtn_clear.setObjectName('btnClear')
        self.tbtn_clear.setFixedHeight(34)
        self.tbtn_clear.clicked.connect(self.clear_results)
        self.tbtn_clear.setEnabled(False)
        toolbar.addWidget(self.tbtn_clear)

    # ---- 中央控件 ----

    def create_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 文件夹路径
        folder_widget = QWidget()
        folder_widget.setObjectName('folderWidget')
        folder_layout = QHBoxLayout(folder_widget)
        folder_layout.setContentsMargins(16, 12, 16, 12)

        lbl = QLabel('文件夹：')
        lbl.setStyleSheet('font-size: 13px; color: #424242;')

        self.folder_edit = QLineEdit()
        self.folder_edit.setObjectName('folderPathEdit')
        self.folder_edit.setPlaceholderText('点击"选择文件夹"或直接拖拽文件夹到此处...')
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setAcceptDrops(True)

        # 拖拽支持
        self.folder_edit.dragEnterEvent = self._drag_enter
        self.folder_edit.dragLeaveEvent = self._drag_leave
        self.folder_edit.dropEvent = self._drop_folder

        btn_browse = QPushButton('浏览...')
        btn_browse.setObjectName('btnBrowse')
        btn_browse.clicked.connect(self.browse_folder)

        folder_layout.addWidget(lbl)
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(btn_browse)

        main_layout.addWidget(folder_widget)

        # 统计面板
        self.stats_widget = StatsWidget()
        main_layout.addWidget(self.stats_widget)

        # 进度条 + 取消按钮
        progress_container = QWidget()
        progress_container.setContentsMargins(16, 4, 16, 4)
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(True)
        self.progress_label = QLabel('')
        self.progress_label.setStyleSheet('color: #757575; font-size: 11px;')

        self.cancel_button = QPushButton('取消')
        self.cancel_button.setObjectName('btnCancel')
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.hide()

        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.cancel_button)
        main_layout.addWidget(progress_container)

        # 表格和详情面板
        splitter = QSplitter(Qt.Horizontal)
        splitter.setContentsMargins(16, 4, 16, 8)

        # 表格
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        # 搜索栏（带 300ms 防抖）
        self.search_bar = QLineEdit()
        self.search_bar.setObjectName('searchBar')
        self.search_bar.setPlaceholderText('搜索发票...')
        self.search_bar.setClearButtonEnabled(True)

        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)
        self.search_bar.textChanged.connect(self._search_timer.start)
        table_layout.addWidget(self.search_bar)

        # 表格模型 + 筛选代理
        self.table_model = InvoiceTableModel()
        self.filter_proxy = InvoiceFilterProxy()
        self.filter_proxy.setSourceModel(self.table_model)

        self.table_view = QTableView()
        self.table_view.setModel(self.filter_proxy)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setShowGrid(False)
        self.table_view.verticalHeader().hide()
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table_view.setColumnWidth(0, 200)
        self.table_view.setColumnWidth(1, 180)
        self.table_view.setColumnWidth(2, 100)
        self.table_view.setColumnWidth(3, 70)
        self.table_view.setColumnWidth(4, 90)
        self.table_view.clicked.connect(self.on_table_clicked)
        self.table_view.doubleClicked.connect(self.open_pdf)

        table_layout.addWidget(self.table_view)

        # 详情面板
        detail_container = QWidget()
        detail_container.setObjectName('detailPanel')
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(12, 12, 12, 12)

        self.preview_label = PdfPreviewLabel()

        detail_title = QLabel('发票详情')
        detail_title.setObjectName('detailTitle')

        self.detail_browser = QTextBrowser()
        self.detail_browser.setObjectName('detailContent')
        self.detail_browser.setPlaceholderText('选择一条发票记录查看详情')
        self.detail_browser.setOpenExternalLinks(False)
        self.detail_browser.setMinimumWidth(280)

        detail_layout.addWidget(self.preview_label)
        detail_layout.addWidget(detail_title)
        detail_layout.addWidget(self.detail_browser, 1)

        splitter.addWidget(table_container)
        splitter.addWidget(detail_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        main_layout.addWidget(splitter, 1)

    # ---- 状态栏 ----

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel('就绪')
        self.status_bar.addWidget(self.status_label, 1)

    # ---- 信号连接 ----

    def connect_signals(self):
        pass

    # ---- 拖拽支持 ----

    def _set_drag_hover(self, active):
        """切换拖拽高亮状态"""
        self.folder_edit.setProperty('dragHover', active)
        self.folder_edit.style().unpolish(self.folder_edit)
        self.folder_edit.style().polish(self.folder_edit)

    def _drag_enter(self, event):
        if event.mimeData().hasUrls():
            self._set_drag_hover(True)
            event.acceptProposedAction()

    def _drag_leave(self, event):
        self._set_drag_hover(False)

    def _drop_folder(self, event):
        self._set_drag_hover(False)
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.set_folder(path)

    # ---- 核心操作 ----

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, '选择包含PDF发票的文件夹', self.settings.value('last_folder', '')
        )
        if folder:
            self.set_folder(folder)

    def _update_recent_menu(self):
        """重建最近文件夹菜单"""
        self.recent_menu.clear()
        folders = self.settings.value('history/folders', [])
        if not folders:
            empty = self.recent_menu.addAction('（无）')
            empty.setEnabled(False)
            return
        for f in folders:
            act = self.recent_menu.addAction(f)
            act.triggered.connect(lambda checked, path=f: self.set_folder(path))

    def _add_to_recent(self, folder):
        """将文件夹加入最近列表（最多 10 个）"""
        folders = self.settings.value('history/folders', [])
        if folder in folders:
            folders.remove(folder)
        folders.insert(0, folder)
        self.settings.setValue('history/folders', folders[:10])
        self._update_recent_menu()

    def set_folder(self, folder):
        self.folder_edit.setText(folder)
        self.settings.setValue('last_folder', folder)
        self._add_to_recent(folder)

        # 扫描PDF文件（递归子文件夹）
        pdf_files = scan_pdf_files_recursive(folder)
        if not pdf_files:
            QMessageBox.information(self, '提示', '该文件夹下没有找到PDF文件')
            self.tbtn_start.setEnabled(False)
            self.act_start.setEnabled(False)
            self.stats_widget.update_stats(0, 0, 0, 0)
            self.setWindowTitle('数电发票识别工具')
            return

        self.pdf_files = pdf_files
        self.tbtn_start.setEnabled(True)
        self.act_start.setEnabled(True)
        self.status_label.setText(f'已找到 {len(pdf_files)} 个PDF文件')
        self.stats_widget.update_stats(len(pdf_files), 0, 0, 0)
        self.setWindowTitle(f'数电发票识别工具 — {Path(folder).name} ({len(pdf_files)} 个文件)')

    @Slot()
    def start_scan(self):
        if not hasattr(self, 'pdf_files') or not self.pdf_files:
            return

        # 清空上次结果（跳过确认）
        self.clear_results(confirmed=True)

        # 禁用按钮
        self.tbtn_start.setEnabled(False)
        self.act_start.setEnabled(False)
        self.tbtn_browse.setEnabled(False)
        self.folder_edit.setEnabled(False)

        # 进度条
        self.progress_bar.setMaximum(len(self.pdf_files))
        self.progress_bar.setValue(0)
        self.progress_label.setText('准备扫描...')
        self.cancel_button.show()
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText('取消')

        # 启动后台线程
        self.worker = ScanWorker(self.pdf_files)
        self.worker.progress.connect(self.on_scan_progress)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.start()

    @Slot()
    def cancel_scan(self):
        """取消扫描，保留已完成的局部结果"""
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.cancel_button.setText('取消中...')
            self.status_label.setText('正在取消...')

    @Slot(int, int, str, dict)
    def on_scan_progress(self, current, total, pdf_path, data):
        self.progress_bar.setValue(current)
        filename = Path(pdf_path).name
        self.progress_label.setText(f'({current}/{total}) {filename}')
        self.status_label.setText(f'正在识别 ({current}/{total})...')

        # 实时更新统计
        r_total = current
        r_success = getattr(self, '_scan_success', 0)
        r_failed = getattr(self, '_scan_failed', 0)
        r_amount = getattr(self, '_scan_amount', 0.0)
        if 'error' in data:
            r_failed += 1
        else:
            r_success += 1
            val = data.get('价税合计')
            if isinstance(val, (int, float)):
                r_amount += val
        self._scan_success = r_success
        self._scan_failed = r_failed
        self._scan_amount = r_amount
        self.stats_widget.update_stats(r_total, r_success, r_failed, r_amount)

    @Slot(list)
    def on_scan_finished(self, results):
        self.results = results
        self.table_model.set_results(results)
        self.filter_proxy.set_filter_text(self.search_bar.text())

        # 恢复按钮
        self.tbtn_start.setEnabled(True)
        self.act_start.setEnabled(True)
        self.tbtn_browse.setEnabled(True)
        self.folder_edit.setEnabled(True)
        self.progress_label.setText('完成')
        self.cancel_button.hide()

        # 更新统计
        total = len(results)
        success = total - self.table_model.get_error_count()
        failed = self.table_model.get_error_count()
        amount = self.table_model.get_total_amount()
        self.stats_widget.update_stats(total, success, failed, amount)

        # 更新按钮状态
        has_data = len(self.results) > 0
        has_success = success > 0
        self.tbtn_export.setEnabled(has_success)
        self.tbtn_clear.setEnabled(has_data)
        self.act_export.setEnabled(has_success)
        self.act_clear.setEnabled(has_data)

        # 扫描完成提示音
        QApplication.beep()

        # 更新窗口标题
        folder_name = Path(self.folder_edit.text()).name if self.folder_edit.text() else ''
        self.setWindowTitle(
            f'数电发票识别工具{f" — {folder_name}" if folder_name else ""} ({success} 张发票)'
        )

        # 状态信息
        if failed > 0 and success > 0:
            self.status_label.setText(
                f'扫描完成：共 {total} 个，成功 {success} 个，失败 {failed} 个'
            )
            QMessageBox.warning(
                self,
                '扫描完成',
                f'扫描完成！\n成功: {success}  失败: {failed}\n金额合计: ¥{amount:.2f}',
            )
        elif success > 0:
            self.status_label.setText(f'扫描完成：{total} 个全部识别成功，金额合计 ¥{amount:.2f}')
        else:
            self.status_label.setText('扫描完成：全部失败')
            QMessageBox.critical(
                self, '扫描失败', '所有文件识别失败，请检查PDF是否为有效的数电发票格式'
            )

        self.worker = None

    def export_data(self):
        """导出数据（Excel 或 CSV），按项目明细行展开"""
        success_results = [r for r in self.results if 'error' not in r[0]]
        if not success_results:
            QMessageBox.warning(self, '提示', '没有可导出的数据')
            return

        # 选择导出字段
        from .export_dialog import FieldSelectDialog

        dlg = FieldSelectDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        selected_fields = dlg.selected_fields()
        if not selected_fields:
            QMessageBox.warning(self, '提示', '请至少选择一个导出字段')
            return

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = self.folder_edit.text() or str(Path.home())

        output_path, fmt = QFileDialog.getSaveFileName(
            self,
            '导出数据',
            str(Path(folder) / f'发票信息_{ts}.xlsx'),
            'Excel文件 (*.xlsx);;CSV文件 (*.csv)',
        )
        if not output_path:
            return

        try:
            flat_results = flatten_results(success_results)
            is_csv = output_path.lower().endswith('.csv')

            if is_csv:
                export_to_csv(flat_results, output_path, fields=selected_fields)
                btn_text = '打开文件'
            else:
                export_to_excel(flat_results, output_path, fields=selected_fields)
                btn_text = '打开Excel'

            msg = QMessageBox(self)
            msg.setWindowTitle('导出成功')
            msg.setText(f'已导出 {len(flat_results)} 条记录（{len(success_results)} 张发票）')
            msg.setInformativeText(str(output_path))
            msg.setIcon(QMessageBox.Information)

            msg.addButton('关闭', QMessageBox.AcceptRole)
            btn_open = msg.addButton(btn_text, QMessageBox.ActionRole)

            msg.exec()

            if msg.clickedButton() == btn_open:
                QDesktopServices.openUrl(QUrl.fromLocalFile(output_path))

            self.status_label.setText(f'已导出到：{output_path}')
        except Exception as e:
            ext = 'CSV' if output_path.lower().endswith('.csv') else 'Excel'
            QMessageBox.critical(self, '导出失败', f'导出{ext}时出错：\n{e}')

    def clear_results(self, confirmed=False):
        """清空结果（若有关联按钮操作则跳过确认）"""
        if not confirmed and self.results:
            reply = QMessageBox.question(
                self,
                '确认清空',
                '确定要清空所有识别结果吗？',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return
        self.results.clear()
        self.table_model.set_results([])
        self.search_bar.clear()
        self.detail_browser.clear()
        self.preview_label.clear_preview()
        self.progress_bar.setValue(0)
        self.progress_label.setText('')
        self.cancel_button.hide()
        self.stats_widget.update_stats(0, 0, 0, 0)
        self.tbtn_export.setEnabled(False)
        self.tbtn_clear.setEnabled(False)
        self.act_export.setEnabled(False)
        self.act_clear.setEnabled(False)
        self.status_label.setText('就绪')
        self.setWindowTitle('数电发票识别工具')

    def _do_search(self):
        """执行搜索过滤（防抖后调用）"""
        if hasattr(self, 'filter_proxy'):
            self.filter_proxy.set_filter_text(self.search_bar.text())

    def open_pdf(self, index):
        """双击行打开 PDF 文件"""
        source_index = self.filter_proxy.mapToSource(index)
        row = source_index.row()
        result = self.table_model.get_result(row)
        if result is None:
            return
        _, pdf_path = result
        if os.path.exists(pdf_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(pdf_path))

    def on_table_clicked(self, index):
        """表格点击 -> 显示详情"""
        source_index = self.filter_proxy.mapToSource(index)
        row = source_index.row()
        result = self.table_model.get_result(row)
        if result is None:
            return
        data_dict, pdf_path = result

        # PDF 预览
        self.preview_label.show_preview(pdf_path)

        if 'error' in data_dict:
            html = (
                f'<h3 style="color:#c62828;">识别失败</h3>'
                f'<p style="color:#757575;">错误信息：</p>'
                f'<p style="color:#c62828;">{data_dict["error"]}</p>'
            )
        else:
            # 基本信息
            html = '<h3 style="color:#1976d2;margin:0 0 8px 0;">发票信息</h3><table>'
            highlight_keys = {'价税合计', '发票号码', '价税合计大写'}
            for field_name, key in BASIC_FIELDS:
                if key in ('文件名',):
                    continue
                value = data_dict.get(key, '')
                if value:
                    is_hl = key in highlight_keys
                    c = '#1976d2' if is_hl else '#424242'
                    fw = 'bold' if is_hl else 'normal'
                    html += (
                        f'<tr><td style="color:#9e9e9e;padding:2px 12px 2px 0;'
                        f'white-space:nowrap;">{field_name}</td>'
                        f'<td style="color:{c};padding:2px 0;font-weight:{fw};">'
                        f'{value}</td></tr>'
                    )
            html += '</table>'

            # 项目明细
            items = data_dict.get('_items', [])
            if items:
                html += '<hr style="border:none;border-top:1px solid #eee;margin:12px 0;">'
                html += '<h3 style="color:#1976d2;margin:0 0 8px 0;">项目明细</h3>'
                for idx, item in enumerate(items, 1):
                    html += f'<p style="color:#757575;margin:4px 0 2px;font-size:11px;">--- 项目 {idx} ---</p>'
                    html += '<table>'
                    for field_name, key in ITEM_FIELDS:
                        value = item.get(key, '')
                        if value:
                            html += (
                                f'<tr><td style="color:#9e9e9e;padding:2px 12px 2px 0;'
                                f'white-space:nowrap;">{field_name}</td>'
                                f'<td style="color:#424242;padding:2px 0;">{value}</td></tr>'
                            )
                    html += '</table>'

            html += (
                f'<hr style="border:none;border-top:1px solid #eee;margin:8px 0;">'
                f'<p style="color:#bdbdbd;font-size:11px;">{pdf_path}</p>'
            )

        self.detail_browser.setHtml(html)

    def show_about(self):
        from .. import __app_name__, __version__

        msg = QMessageBox(self)
        msg.setWindowTitle(f'关于 {__app_name__}')
        msg.setIcon(QMessageBox.Information)
        msg.setText(
            f'<h3>{__app_name__}</h3>'
            f'<p>版本: {__version__}</p>'
            f'<p>用于识别数电发票（PDF格式）并将信息导出到Excel表格。</p>'
            f'<hr>'
            f'<p style="color:#757575;font-size:11px;">'
            f'基于 PySide6 + pdfplumber + openpyxl 构建</p>'
            f'<hr>'
            f'<p style="margin:4px 0;">'
            f'作者：<b>陈凡是我</b>'
            f'</p>'
            f'<p style="margin:4px 0;">'
            f'抖音号：<b>seed1994</b>'
            f'  ·  微信号：<b>jishukong66</b>'
            f'</p>'
            f'<p style="margin:0;">'
            f'GitHub：'
            f'<a href="https://github.com/metahuber/fapiao-shibie" style="color:#1976d2;">'
            f'github.com/metahuber/fapiao-shibie</a>'
            f'</p>'
        )
        # 让链接可点击
        label = msg.findChild(QLabel)
        if label:
            label.setOpenExternalLinks(True)
        msg.exec()

    def restore_settings(self):
        """恢复设置"""
        size = self.settings.value('window/size')
        if size:
            self.resize(size)
        pos = self.settings.value('window/position')
        if pos:
            self.move(pos)
        # 恢复列宽
        col_widths = self.settings.value('table/column_widths')
        if col_widths is not None:
            for col, w in enumerate(col_widths):
                if w:
                    self.table_view.setColumnWidth(col, int(w))

    def save_settings(self):
        """保存设置"""
        self.settings.setValue('window/size', self.size())
        self.settings.setValue('window/position', self.pos())
        # 保存列宽
        widths = []
        for col in range(self.table_model.column_count):
            widths.append(self.table_view.columnWidth(col))
        self.settings.setValue('table/column_widths', widths)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait(3000)
        self.save_settings()
        super().closeEvent(event)
