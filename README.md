# 发票识别工具

自动扫描文件夹中的 PDF 发票（数电发票 / 增值税电子普通发票），提取关键信息并导出到 Excel。

## 功能

- **选择文件夹或拖拽文件夹**到窗口，自动递归扫描所有 PDF
- **自动识别发票类型** — 数电发票和增值税电子普通发票无需手动选择
- **支持 29 个字段**的完整提取（21 项基本信息 + 8 项项目明细）
- **PDF 预览** — 点击侧边栏缩略图即可放大查看发票（支持滚轮缩放）
- **后台线程处理**，大量文件也不卡界面
- **Excel 导出**（合并单元格模式）：
  - 发票级字段（如发票号码、购买方名称、价税合计等）合并单元格
  - 项目明细逐行展开
  - 自动筛选 + 冻结首行
- **CSV 导出**（每张发票一行，项目明细合并为文本）
- **失败文件可视化** — 识别失败的发票在列表中显示文件名和错误原因（红色背景）

## 提取字段

| 类别 | 字段 |
|------|------|
| 基本信息（21个） | 文件名、发票类型、发票代码、发票号码、开票日期、机器编号、校验码、购买方名称、购买方纳税人识别号、购买方地址电话、购买方开户行及账号、销售方名称、销售方纳税人识别号、销售方地址电话、销售方开户行及账号、价税合计大写、价税合计（小写）、备注、收款人、复核、开票人 |
| 项目明细（8个） | 项目名称、规格型号、单位、数量、单价、金额、税率、税额 |

## 快速开始

```bash
# 安装依赖
pip install PySide6 pdfplumber openpyxl

# （可选）PDF 预览需要
pip install PyMuPDF

# 运行
python -X utf8 -m InvoiceApp
```

或双击 `run_pyside6.bat`。

## 项目结构

```
InvoiceApp/
├── core/
│   ├── parser.py           # 数电发票解析引擎
│   ├── parser_normal.py    # 增值税电子普通发票解析引擎
│   ├── parser_factory.py   # 自动识别发票类型并分派
│   └── exporter.py         # Excel/CSV 导出
├── ui/
│   ├── main_window.py      # 主窗口
│   ├── worker.py           # 后台扫描线程
│   ├── pdf_preview.py      # PDF 预览（支持点击放大）
│   ├── export_dialog.py    # 导出字段选择对话框
│   ├── resources.py        # 图标和样式加载
│   └── donate_dialog.py    # 打赏弹窗
├── resources/
│   ├── style.qss           # Qt 样式表
│   ├── weixin_shoukuan.png
│   └── zhifubao_shoukuan.png
└── __main__.py             # 入口

build.bat       # 打包安装包
installer.iss   # Inno Setup 配置
publish.bat     # 一键打包+发布到 GitHub Releases
pyproject.toml  # 项目元数据
ruff.toml       # 代码格式配置
```

## 技术栈

Python 3.11+、PySide6、pdfplumber、openpyxl、PyMuPDF（可选）、ruff

## 支持作者

如果这个工具对你有帮助，欢迎打赏支持！

<p align="center">
  <img src="weixin_shoukuan.png" width="200" alt="微信收款码">
  &nbsp;&nbsp;&nbsp;&nbsp;
  <img src="zhifubao_shoukuan.png" width="200" alt="支付宝收款码">
</p>
<p align="center">微信收款码&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;支付宝收款码</p>