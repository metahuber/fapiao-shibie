"""Excel 导出模块 — 扁平格式（每条项目明细一行）"""

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

from .parser import BASIC_FIELDS, ITEM_FIELDS

# 样式
HEADER_FONT = Font(name='微软雅黑', bold=True, size=11, color='FFFFFF')
HEADER_FILL = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
HEADER_ALIGNMENT = Alignment(horizontal='center', vertical='center', wrap_text=True)
CELL_FONT = Font(name='微软雅黑', size=10)
CELL_ALIGNMENT = Alignment(horizontal='left', vertical='center')
THIN_BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin'),
)


def export_to_excel(results, output_path):
    """导出到Excel，每条项目明细占一行

    results: [(data_dict, pdf_path), ...]
    """
    wb = Workbook()
    ws = wb.active
    ws.title = '发票信息'

    # 表头 = 基本信息 + 项目明细
    all_fields = BASIC_FIELDS + ITEM_FIELDS
    headers = [f[0] for f in all_fields]
    headers.append('文件路径')

    _write_header(ws, headers)
    _write_data(ws, results, all_fields)
    _format_sheet(ws, headers)

    wb.save(output_path)
    return output_path


def _write_header(ws, headers):
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER


def _write_data(ws, results, all_fields):
    """逐行写入数据（已展开为每项目明细一行的扁平格式）"""
    for row_idx, (data_dict, pdf_path) in enumerate(results, 2):
        if 'error' in data_dict:
            continue
        for col, (_, key) in enumerate(all_fields, 1):
            value = data_dict.get(key, '')
            if isinstance(value, float):
                value = round(value, 2)
            cell = ws.cell(row=row_idx, column=col, value=value)
            cell.font = CELL_FONT
            cell.alignment = CELL_ALIGNMENT
            cell.border = THIN_BORDER

        # 最后一列：文件路径
        col = len(all_fields) + 1
        cell = ws.cell(row=row_idx, column=col, value=str(pdf_path))
        cell.font = CELL_FONT
        cell.alignment = CELL_ALIGNMENT
        cell.border = THIN_BORDER


def _format_sheet(ws, headers):
    """设置列宽、冻结、筛选"""
    col_count = len(headers)

    # 列宽
    widths = {
        0: 30, 1: 24, 2: 16, 3: 30, 4: 24,
        5: 30, 6: 24, 7: 20, 8: 12,
        9: 20, 10: 16, 11: 16, 12: 10,
        13: 10, 14: 10, 15: 12, 16: 12,
    }
    for i in range(col_count):
        col_letter = chr(65 + i) if i < 26 else chr(64 + i // 26) + chr(65 + i % 26)
        ws.column_dimensions[col_letter].width = widths.get(i, 15)

    # 冻结首行
    ws.freeze_panes = 'A2'

    # 自动筛选
    last_col = chr(65 + col_count - 1) if col_count <= 26 else 'Z'
    ws.auto_filter.ref = f'A1:{last_col}{ws.max_row}'
