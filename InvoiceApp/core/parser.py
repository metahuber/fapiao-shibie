"""数电发票 PDF 解析模块 — 通用版"""

import re
from pathlib import Path
import pdfplumber


# ==================== 字段定义 ====================

# 发票基本信息字段
BASIC_FIELDS = [
    ('文件名', '文件名'),
    ('发票号码', '发票号码'),
    ('开票日期', '开票日期'),
    ('购买方名称', '购买方名称'),
    ('购买方纳税人识别号', '购买方纳税人识别号'),
    ('销售方名称', '销售方名称'),
    ('销售方纳税人识别号', '销售方纳税人识别号'),
    ('价税合计（大写）', '价税合计大写'),
    ('价税合计（小写）', '价税合计'),
    ('备注', '备注'),
    ('开票人', '开票人'),
]

# 项目明细字段
ITEM_FIELDS = [
    ('项目名称', '项目名称'),
    ('规格型号', '规格型号'),
    ('单位', '单位'),
    ('数量', '数量'),
    ('单价', '单价'),
    ('金额', '金额'),
    ('税率/征收率', '税率/征收率'),
    ('税额', '税额'),
]

# 导出时使用的完整列定义：基本信息 + 项目明细
EXPORT_FIELDS = BASIC_FIELDS + ITEM_FIELDS

# 列名识别：按优先级从精确到模糊
COLUMN_MATCHERS = [
    ('项目名称', '项目名称'),
    ('规格型号', '规格型号'),
    ('税率/征收率', '税率/征收率'),
    ('征收率', '税率/征收率'),
    ('规格', '规格型号'),
    ('型号', '规格型号'),
    ('单位', '单位'),
    ('数量', '数量'),
    ('单价', '单价'),
    ('金额', '金额'),
    ('税率', '税率/征收率'),
    ('税额', '税额'),
]


# ==================== 基本信息解析 ====================

def _extract_basic_info(text, lines):
    """提取发票基本信息"""
    data = {}

    # 发票号码
    m = re.search(r'发票号码[：:]\s*(\S+)', text)
    if m:
        data['发票号码'] = m.group(1).strip()

    # 开票日期
    m = re.search(r'开票日期[：:]\s*(\S+)', text)
    if m:
        data['开票日期'] = m.group(1).strip()

    # 购买方名称 & 销售方名称（同一行格式：买 名称：XXX 售 名称：YYY）
    found_names = False
    for line in lines:
        if '名称' in line and '售' in line:
            m_buyer = re.search(r'名称[：:]\s*(.+?)\s+售\s+名称[：:]', line)
            if m_buyer:
                data['购买方名称'] = m_buyer.group(1).strip()
            m_seller = re.search(r'售\s+名称[：:]\s*(.+)', line)
            if m_seller:
                data['销售方名称'] = m_seller.group(1).strip()
            found_names = True
            break
    if not found_names:
        # 备用：分别查找
        for line in lines:
            if '购买方' in line and '名称' in line:
                m = re.search(r'名称[：:]\s*(.+)', line)
                if m:
                    data['购买方名称'] = m.group(1).strip()
            if '销售方' in line and '名称' in line:
                m = re.search(r'名称[：:]\s*(.+)', line)
                if m:
                    data['销售方名称'] = m.group(1).strip()

    # 纳税人识别号
    tax_ids = re.findall(r'纳税人识别号[）\)]?[：:]\s*(\w+)', text)
    if len(tax_ids) >= 2:
        data['购买方纳税人识别号'] = tax_ids[0]
        data['销售方纳税人识别号'] = tax_ids[1]
    elif len(tax_ids) == 1:
        data['购买方纳税人识别号'] = tax_ids[0]

    # 价税合计（小写）
    m = re.search(r'价税合计.*?小写[）\)]?\s*[¥￥]?\s*([\d.,]+)', text)
    if m:
        raw = m.group(1).replace(',', '')
        data['价税合计'] = float(raw)

    # 价税合计（大写）
    m = re.search(r'价税合计（大写）\s*(.+?)（小写）', text)
    if m:
        data['价税合计大写'] = m.group(1).strip()

    # 开票人
    m = re.search(r'开票人[：:]\s*(\S+)', text)
    if m:
        data['开票人'] = m.group(1).strip()

    # 备注：从"备注"开始到"开票人"之间的所有内容
    remark_parts = []
    in_remark = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('备注') or stripped.startswith('备 '):
            # "备注" 所在行，取冒号后的内容
            m = re.search(r'备注[：:]\s*(.*)', stripped)
            if m:
                remark_parts.append(m.group(1))
            else:
                # 可能在同一行的后半部分
                m = re.search(r'备\s*注[：:]\s*(.*)', stripped)
                if m:
                    remark_parts.append(m.group(1))
            in_remark = True
            continue
        if in_remark:
            if '开票人' in stripped:
                break
            if stripped:
                remark_parts.append(stripped)
    if remark_parts:
        data['备注'] = '\n'.join(p for p in remark_parts if p)

    return data


# ==================== 项目明细解析 ====================

def _find_header_columns(header_line):
    """从表头行识别列名及对应的标准名称

    返回: [(column_index, standard_name), ...]
    """
    # 按空白分割表头，得到各列的文本片段
    parts = header_line.split()
    col_names = []
    for p in parts:
        p = p.strip()
        if p:
            col_names.append(p)

    if len(col_names) < 3:
        return []

    # 将每个片段映射到标准列名
    result = []
    for i, name in enumerate(col_names):
        matched = False
        for pattern, std_name in COLUMN_MATCHERS:
            if pattern in name or name in pattern:
                result.append((i, std_name))
                matched = True
                break
        if not matched:
            result.append((i, name))

    return result


def _parse_items_table(lines):
    """从文本行中提取项目明细表"""
    items = []

    # 找表头行
    header_idx = None
    for i, line in enumerate(lines):
        if '项目名称' in line:
            header_idx = i
            break

    if header_idx is None:
        return items

    header_line = lines[header_idx]
    col_info = _find_header_columns(header_line)

    if len(col_info) < 3:
        return items

    expected_cols = len(col_info)

    # 解析数据行
    for j in range(header_idx + 1, len(lines)):
        line = lines[j]
        stripped = line.strip()

        if not stripped:
            continue

        # 结束条件
        if re.search(r'[合合计]\s*计', stripped) or stripped.startswith('价税合计'):
            break
        if '项目名称' in stripped:
            continue

        # 按空白分割取值
        parts = stripped.split()
        item = {}
        if len(parts) >= expected_cols:
            # 正好匹配或超出 — 直接映射
            for col_idx, std_name in col_info:
                item[std_name] = parts[col_idx] if col_idx < len(parts) else ''
        elif len(parts) >= 3:
            # 列数不匹配但至少有3列，取前几列
            for col_idx, std_name in col_info[:len(parts)]:
                item[std_name] = parts[col_idx]

        if item and item.get('项目名称', '').strip():
            items.append(item)

    return items


# ==================== 主解析函数 ====================

def parse_invoice_text(text):
    """解析数电发票文本

    返回:
        dict: {
            '发票号码': '...',
            '开票日期': '...',
            ...
            '_items': [                    # 项目明细集合
                {'项目名称': '...', '金额': '...', ...},
                ...
            ]
        }
    """
    lines = text.split('\n')

    # 1. 提取基本信息
    data = _extract_basic_info(text, lines)

    # 2. 提取项目明细
    items = _parse_items_table(lines)
    data['_items'] = items

    return data


# ==================== 文件处理 ====================

def process_pdf(pdf_path):
    """处理单个PDF文件，返回 (data_dict, pdf_path)

    解析结果包含:
        - 基本信息字段
        - _items: 项目明细列表（每个项目是一个 dict）
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''.join(page.extract_text() or '' for page in pdf.pages)
            if not text.strip():
                return {'error': '无法提取文本内容'}, pdf_path
            data = parse_invoice_text(text)
            data['文件名'] = Path(pdf_path).name
            return data, pdf_path
    except Exception as e:
        return {'error': str(e)}, pdf_path


def scan_pdf_files(folder_path):
    """扫描文件夹下所有PDF文件"""
    return [
        str(p) for p in sorted(Path(folder_path).iterdir())
        if p.suffix.lower() == '.pdf'
    ]


def scan_pdf_files_recursive(folder_path):
    """递归扫描文件夹下所有PDF文件"""
    return [
        str(p) for p in sorted(Path(folder_path).rglob('*.pdf'))
    ]


# ==================== 结果展开 ====================

def flatten_results(results):
    """将解析结果展开为导出用的一行行数据

    每条发票可能对应多行（每条项目明细一行），
    基本信息重复出现在每一行中，项目字段覆盖基本信息中的同名键。

    Args:
        results: [(data_dict, pdf_path), ...]

    Returns:
        [(flat_dict, pdf_path), ...]
    """
    flat = []
    for data, pdf_path in results:
        if 'error' in data:
            continue
        items = data.get('_items', [])
        # 移除_items本身，不参与导出
        base = {k: v for k, v in data.items() if k != '_items'}
        if not items:
            flat.append((base, pdf_path))
        else:
            for item in items:
                row = dict(base)
                # 项目字段覆盖到顶层（不存在键名冲突，但防万一）
                row.update(item)
                flat.append((row, pdf_path))
    return flat

