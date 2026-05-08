# 数电发票 PDF 识别导出工具

自动扫描文件夹中的数电发票 PDF，提取关键信息并导出到 Excel 表格。

## 功能

- 选择文件夹或拖拽文件夹到窗口，自动扫描所有 PDF
- 识别全国统一格式的数电发票信息
- 导出为格式化 Excel（按项目明细行展开，带筛选和冻结首行）
- 后台线程处理，不卡界面

## 提取字段

| 类别 | 字段 |
|------|------|
| 基本信息 | 发票号码、开票日期、购买方名称及税号、销售方名称及税号、价税合计（大小写）、备注、开票人 |
| 项目明细 | 项目名称、规格型号、单位、数量、单价、金额、税率/征收率、税额 |

## 快速开始

```bash
# 安装依赖
pip install PySide6 pdfplumber openpyxl

# 运行
python -X utf8 -m InvoiceApp
```

或双击 `run_pyside6.bat`。

## 项目结构

```
InvoiceApp/          # PySide6 桌面应用（主力版本）
├── core/
│   ├── parser.py    # PDF 解析引擎
│   └── exporter.py  # Excel 导出
├── ui/
│   ├── main_window.py  # 主窗口
│   ├── worker.py       # 后台扫描线程
│   └── resources.py    # 图标和样式
├── resources/style.qss # Qt 样式表
└── __main__.py         # 入口

legacy_tkinter.py    # tkinter 版（旧版保留）
pyproject.toml        # 项目元数据
ruff.toml             # 代码格式配置
```

## 技术栈

Python 3.11+、PySide6、pdfplumber、openpyxl、ruff
