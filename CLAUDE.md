# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

Two versions of the same app coexist:

- **InvoiceApp/** — PySide6 GUI version (active development)
- **legacy_tkinter.py** — tkinter version (legacy, retained as reference)

### Core Data Flow

```
PDF files
  → pdfplumber extracts text
    → parser.py parses into {basic_info_fields..., _items: [{项目明细}, ...]}
      → UI displays in QTableView + detail panel
        → exporter.py flattens to one-row-per-item Excel
```

### Key Files

| File | Role |
|------|------|
| `InvoiceApp/core/parser.py` | PDF text → structured data. Defines `BASIC_FIELDS`, `ITEM_FIELDS`, `COLUMN_MATCHERS`. `parse_invoice_text()` returns dict with `_items` list. `flatten_results()` expands items into flat rows for export. |
| `InvoiceApp/core/exporter.py` | Takes flattened results, writes formatted `.xlsx` via openpyxl |
| `InvoiceApp/ui/main_window.py` | QMainWindow with toolbar, stats panel, QTableView, detail panel, status bar |
| `InvoiceApp/ui/worker.py` | QThread subclass for background PDF scanning |
| `InvoiceApp/ui/resources.py` | SVG icon generation and QSS loading |
| `InvoiceApp/resources/style.qss` | Qt stylesheet (Material-like flat design) |
| `InvoiceApp/__main__.py` | Entry point: `python -m InvoiceApp` |

### Parser Data Model

Single invoice parse result:
```python
{
    '文件名': 'store_xxx.pdf',
    '发票号码': '26377000000217799578',
    '开票日期': '2026年03月06日',
    '购买方名称': '...',
    '购买方纳税人识别号': '...',
    '销售方名称': '...',
    '销售方纳税人识别号': '...',
    '价税合计大写': '壹拾伍元整',
    '价税合计': 15.0,
    '备注': '...',
    '开票人': '...',
    '_items': [  # 项目明细集合
        {
            '项目名称': '*经营租赁*通行费',
            '规格型号': '货车',
            '单位': '次',
            '数量': '1',
            '单价': '15.00',
            '金额': '15.00',
            '税率/征收率': '***',
            '税额': '***',
        },
    ],
}
```

Export uses `flatten_results()` to merge each item with basic info into one flat dict per row.

### Parser Design Notes

- Column matching uses `COLUMN_MATCHERS` ordered list (precise patterns first) to avoid substring collision (e.g. "规格型号" before "规格")
- Item table rows are split by whitespace, mapped 1:1 to header columns
- `备注` extraction: collects lines between "备注" and "开票人"
- `_parse_items_table()` uses whitespace-split rather than position-based parsing for reliability

### UI Design Notes

- Toolbar buttons use `QPushButton` widgets instead of `QAction` icons for reliable rendering across Windows DPI/theme settings
- Background scanning via `ScanWorker` (QThread) so UI stays responsive
- Window geometry and last folder path persisted via `QSettings`
- Drag-and-drop folder support via `QLineEdit` event overrides

## Commands

```bash
# Run the app (PySide6 version)
python -X utf8 -m InvoiceApp

# Or double-click
run_pyside6.bat

# Install dependencies
pip install PySide6 pdfplumber openpyxl

# Run legacy tkinter version
python -X utf8 legacy_tkinter.py
```

## Git

Remote: `git@github.com:metahuber/fapiao-shibie.git` (SSH)
