"""增值税电子普通发票 PDF 解析模块

解析策略：
  1. extract_tables() 提取主表格 → 购买方/销售方/价税合计/备注
  2. extract_text() 提取头部信息（发票代码/号码/日期/机器编号/校验码）
  3. extract_text() 提取底部信息（收款人/复核/开票人）
  4. 第二页清单合并到项目明细

"""

import re
from pathlib import Path

import pdfplumber

from .parser import COLUMN_MATCHERS

# ==================== 头部信息（多种格式兼容） ====================


def _extract_header_info(text, lines):
    """提取发票头部：发票代码、发票号码、开票日期、机器编号、校验码"""
    data = {}

    # --- 发票代码 ---
    m = re.search(r'发票代码\s*[：:]\s*(\d{12})', text)
    if m:
        data['发票代码'] = m.group(1)
    else:
        for line in lines:
            line = line.strip()
            if re.match(r'^\d{12}$', line):
                data['发票代码'] = line
                break

    # --- 发票号码 ---
    m = re.search(r'发票号码\s*[：:]\s*(\d{8,})', text)
    if m:
        data['发票号码'] = m.group(1)
    else:
        m = re.search(r'统一发票监[^0-9]*(\d{8})', text)
        if m:
            data['发票号码'] = m.group(1)
    # 根据文件名提取发票号码（最后保障）
    if '发票号码' not in data:
        m = re.search(r'[-](\d{8})[-]', text)
        if m:
            data['发票号码'] = m.group(1)

    # --- 开票日期 ---
    m = re.search(r'开票日期[^\S\n]*[：:][^\S\n]*([^\n]+)', text)
    if m:
        raw = m.group(1).strip()
        if raw and raw != '年 月 日':
            data['开票日期'] = raw
    if '开票日期' not in data:
        # 在"国家税务总局"附近找日期（含 年/月 分隔符）
        m = re.search(r'国家税务总局[^0-9]*(20\d{2})\s*年?\s*(\d{1,2})\s*月?\s*(\d{1,2})', text)
        if m:
            data['开票日期'] = f'{m.group(1)}年{m.group(2)}月{m.group(3)}日'
        else:
            # 更宽松：找任何 20xx年xx月xx日 格式
            m = re.search(r'(20\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
            if m:
                data['开票日期'] = f'{m.group(1)}年{m.group(2)}月{m.group(3)}日'

    # --- 机器编号 ---
    m = re.search(r'机器编号\s*[：:]\s*(\d+)', text)
    if m:
        data['机器编号'] = m.group(1)

    # --- 校验码 ---
    m = re.search(r'校[验]\s*[验]\s*[码]\s*[：:]?\s*([\d\s]{14,})', text)
    if m:
        data['校验码'] = ''.join(m.group(1).split())
    if '校验码' not in data:
        # 机器编号行后面的20位数字（校验码）
        m = re.search(r'机器编号\s*[：:]\s*\d+\s*(?:[一-鿿]+\s*税务[局]\s*)?([\d\s]{14,})', text)
        if m:
            raw = m.group(1).strip()
            parts = raw.split()
            if (len(parts) == 5 and all(len(p) == 4 for p in parts)) or (
                len(parts) == 4 and all(len(p) == 5 for p in parts)
            ):
                data['校验码'] = ''.join(parts)

    return data


# ==================== 购买方/销售方（表格方式） ====================


def _parse_buyer_seller_cell(cell_text):
    """从购买方/销售方单元格文本中解析四个子字段"""
    # 去掉 Chinese characters 之间的空白，方便正则匹配
    # 但保留英文/数字不变
    cell = re.sub(r'(?<=[一-鿿])\s+(?=[一-鿿：:，,、])', '', cell_text)
    cell = cell.replace('\n', ' ')
    data = {}

    m = re.search(r'名称[：:]\s*(.*?)(?:\s*(?:纳税人识别号|$))', cell)
    if m:
        name = m.group(1).strip()
        if name:
            data['名称'] = name

    m = re.search(r'纳税人识别号[：:]\s*([0-9A-Za-z][0-9A-Za-z\s]*[0-9A-Za-z]|[0-9A-Za-z])', cell)
    if m:
        data['纳税人识别号'] = ''.join(m.group(1).split())

    m = re.search(r'地址[、，]?\s*电话[：:]\s*(.*?)(?:\s*(?:开户行|$))', cell)
    if m:
        val = m.group(1).strip()
        if val and val != '..':
            data['地址电话'] = val

    m = re.search(r'开户行[及]?账号[：:]\s*(.*?)$', cell)
    if m:
        val = m.group(1).strip()
        if val and val != '..':
            data['开户行及账号'] = val

    return data


def _find_main_table(pdf):
    """找到第一页的主表格（包含购买方/销售方/项目明细/价税合计）"""
    if not pdf or not pdf.pages:
        return None
    tables = pdf.pages[0].extract_tables()
    if not tables:
        return None
    # 主表格是第一个包含"购"和"买"字样的表格
    for table in tables:
        if len(table) < 3:
            continue
        combined = ''.join(''.join(c or '' for c in row) for row in table)
        if '购' in combined and ('买' in combined or '售' in combined):
            return table
    # 退回到第一个有足够行数的表格
    for table in tables:
        if len(table) >= 3:
            return table
    return None


def _parse_table_data(table):
    """从主表格解析所有数据"""
    data = {'_items': []}

    if not table or len(table) < 3:
        return data

    # === 购买方 Row0 ===
    if len(table) > 0:
        buyer_cell = (table[0] or ['', ''])[1] or ''
        parsed = _parse_buyer_seller_cell(buyer_cell)
        if '名称' in parsed:
            data['购买方名称'] = parsed['名称']
        if '纳税人识别号' in parsed:
            data['购买方纳税人识别号'] = parsed['纳税人识别号']
        if '地址电话' in parsed:
            data['购买方地址电话'] = parsed['地址电话']
        if '开户行及账号' in parsed:
            data['购买方开户行及账号'] = parsed['开户行及账号']

    # === 价税合计 Row2 ===
    for row in table:
        if not row:
            continue
        combined = ''.join(c or '' for c in row).replace('\n', ' ')
        if '价税合计' not in combined:
            continue
        m = re.search(r'价税合计\s*[（(]大写[）)]\s*(.+?)\s*[（(]小写[）)]', combined)
        if m:
            data['价税合计大写'] = m.group(1).strip()
        m = re.search(r'[（(]小写[）)]\s*[¥￥]?\s*([\d,]+\.\d{2})', combined)
        if m:
            data['价税合计'] = float(m.group(1).replace(',', ''))

    # === 销售方 Row3 ===
    if len(table) > 3:
        seller_row = table[3] or ['', '']
        seller_cell = seller_row[1] or ''
        parsed = _parse_buyer_seller_cell(seller_cell)
        if '名称' in parsed:
            data['销售方名称'] = parsed['名称']
        if '纳税人识别号' in parsed:
            data['销售方纳税人识别号'] = parsed['纳税人识别号']
        if '地址电话' in parsed:
            data['销售方地址电话'] = parsed['地址电话']
        if '开户行及账号' in parsed:
            data['销售方开户行及账号'] = parsed['开户行及账号']

        # 备注（Row3 第7列）
        remark_cell = seller_row[7] if len(seller_row) > 7 else ''
        if remark_cell:
            remark = remark_cell.replace('\n', ' ').strip()
            # 去掉"备注"前缀
            remark = re.sub(r'^备\s*注[：:]?\s*', '', remark)
            if remark:
                data['备注'] = remark

    # === 项目明细 Row1（多行数据在一个单元格内，以换行分隔） ===
    items = _parse_items_from_row1(table[1] if len(table) > 1 else None)
    if items:
        data['_items'] = items

    return data


def _parse_items_from_row1(row):
    """从表格 Row1 解析项目明细（每列多个值以换行符分隔）"""
    items = []
    if not row:
        return items

    cells = [c or '' for c in row]

    # 找到有数据的列索引
    col_map = {}
    for ci, cell in enumerate(cells):
        first_line = cell.split('\n')[0].strip()
        if not first_line:
            continue
        # 去掉中文字符间的空格再匹配（如"金 额" → "金额"）
        clean = re.sub(r'(?<=[一-鿿])\s+(?=[一-鿿])', '', first_line)
        for pattern, std_name in COLUMN_MATCHERS:
            if pattern in clean or clean in pattern:
                col_map[ci] = std_name
                break

    if not col_map:
        return items

    # 确定数据行数
    data_rows = 0
    for ci in col_map:
        lines = [v.strip() for v in cells[ci].split('\n') if v.strip() and v.strip() != '.']
        if len(lines) > 1:
            data_rows = max(data_rows, len(lines) - 1)

    if data_rows == 0:
        return items

    # 获取金额列索引
    amount_col = None
    for ci, std_name in col_map.items():
        if std_name == '金额':
            amount_col = ci
            break

    # 构建逐列的数据矩阵
    item_values = []
    for ci in sorted(col_map.keys()):
        lines = [v.strip() for v in cells[ci].split('\n') if v.strip() and v.strip() != '.']
        if len(lines) > 1:
            item_values.append((col_map[ci], lines))
        else:
            item_values.append((col_map[ci], [lines[0] if lines else '']))

    # 用金额列的数值行数作为真实数据行数
    if amount_col is not None:
        amount_lines = [
            v.strip()
            for v in cells[amount_col].split('\n')
            if v.strip() and v.strip() != '.' and not v.strip().startswith('¥')
        ]
        if len(amount_lines) > 1:
            data_rows = len(amount_lines) - 1

    # 逐行提取
    for ri in range(data_rows):
        item = {}
        has_name = False
        for ci in sorted(col_map.keys()):
            lines = [v.strip() for v in cells[ci].split('\n') if v.strip() and v.strip() != '.']
            # 过滤掉合计行和 ¥ 开头行
            filtered = [v for v in lines if v != '合 计' and v != '合计' and not v.startswith('¥')]
            # 第一行是表头，后面的才是数据
            data_part = []
            for v in filtered[1:]:
                data_part.append(v)
            if ri < len(data_part):
                val = data_part[ri]
                if val:
                    item[col_map[ci]] = val
                    if col_map[ci] == '项目名称':
                        has_name = True

        if not has_name:
            continue

        # 跳过纯合计行
        name = item.get('项目名称', '')
        if re.match(r'^合\s*计$', name):
            continue

        # 合并多行项目名称（后一行是前一行续行时）
        if len(items) > 0 and not item.get('金额', '') and name:
            # 金额为空，可能是项目名称续行，合并到上一个项目
            prev = items[-1]
            prev_name = prev.get('项目名称', '')
            if prev_name and not prev_name.endswith('）') and not prev_name.endswith(')'):
                prev['项目名称'] = prev_name + name
                continue

        items.append(item)

    return items


# ==================== 底部信息 ====================


def _parse_bottom_info(text):
    """从文本中提取收款人、复核、开票人"""
    data = {}
    lines = text.split('\n')

    # Type A: 有标签格式（标签内部可能有空格，如 "收 款 人：耿明慧"）
    label_fixes = [
        (r'收\s*款\s*人', '收款人'),
        (r'复\s*核', '复核'),
        (r'开\s*票\s*人', '开票人'),
        (r'销\s*售\s*方', '销售方'),
    ]

    def fix_labels(s):
        for pat, repl in label_fixes:
            s = re.sub(pat, repl, s)
        return s

    label_pat = re.compile(
        r'(?:收款人[：:]\s*)?(\S+)\s+复核[：:]\s*(\S+)'
        r'(?:\s+开票人[：:]\s*(\S+))?'
    )
    for line in reversed(lines):
        fixed = fix_labels(line)
        m = label_pat.search(fixed)
        if m:
            vals = [m.group(i).rstrip('：: ') if m.group(i) else '' for i in (1, 2, 3)]
            found = False
            for val, key in zip(vals, ['收款人', '复核', '开票人']):
                if val and val not in ('收款人', '复核', '开票人', '销售方', '（章）'):
                    data[key] = val
                    found = True
            if found:
                break

    # Type B: 无标签格式 "钱葳 邹莹 刘紫依"
    if '收款人' not in data and '复核' not in data and '开票人' not in data:
        skip_keywords = {
            '规格',
            '单位',
            '金额',
            '税额',
            '税率',
            '数量',
            '单价',
            '价税合计',
            '小写',
            '大写',
            '开户行',
            '地址',
            '电话',
            '纳税人识别号',
            '名称',
            '项目名称',
        }
        name_pat = re.compile(r'^[一-鿿·]{1,6}$')
        for line in reversed(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if any(kw in stripped for kw in skip_keywords):
                continue
            parts = stripped.split()
            if len(parts) >= 3:
                valid = all(name_pat.match(p) for p in parts[:3])
                if valid:
                    data['收款人'] = parts[0]
                    data['复核'] = parts[1]
                    data['开票人'] = parts[2]
                    break

    return data


# ==================== 第二页清单 ====================


def _parse_detail_from_text(text):
    """从文本解析第二页的销售货物或者提供应税劳务清单"""
    items = []
    lines = text.split('\n')

    header_idx = None
    for i, line in enumerate(lines):
        if '货物' in line and '名称' in line and '购买方' not in line and '销售方' not in line:
            header_idx = i
            break
    if header_idx is None:
        for i, line in enumerate(lines):
            if '序号' in line and '名称' in line and '金额' in line:
                header_idx = i
                break
    if header_idx is None:
        return items

    # 列名（含 序号+名称+规格型号+单位+数量+单价+金额+税率+税额）
    # 从右往左映射：金额/税率/税额固定，左边列可能因发票格式缺省
    right_keys = ['金额', '税率', '税额']
    left_keys = ['规格型号', '单位', '数量', '单价']

    for line in lines[header_idx + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if '小计' in stripped or '总计' in stripped or '备注' in stripped:
            break
        parts = stripped.split()
        if len(parts) < 2:
            continue

        name = parts[1]
        if re.match(r'^\d+$', name):
            continue

        item = {'项目名称': name}
        rest = parts[2:]  # 去掉序号和项目名称
        r = len(rest)

        # 从右往左分配：金额、税率、税额（一定有）
        for i, key in enumerate(right_keys):
            idx = r - len(right_keys) + i
            if 0 <= idx < r:
                val = rest[idx]
                if val and val != '.':
                    item[key] = val

        # 剩余中间部分从右往左分配：单价→数量→单位→规格型号
        middle = r - len(right_keys)  # 金额/税率/税额占用的部分
        for i, key in enumerate(reversed(left_keys)):
            idx = middle - 1 - i
            if idx >= 0:
                val = rest[idx]
                if val and val != '.':
                    item[key] = val

        items.append(item)

    return items


def _parse_detail_page(pdf):
    """解析第二页的销售货物或者提供应税劳务清单"""
    items = []

    if not pdf or len(pdf.pages) < 2:
        return items

    tables = pdf.pages[1].extract_tables()
    if not tables:
        return items

    table = tables[0]
    if len(table) < 2:
        return items

    # 找表头行
    header_idx = None
    for i, row in enumerate(table):
        combined = ''.join(c or '' for c in row)
        if '货物' in combined or '劳务' in combined or '项目名称' in combined:
            header_idx = i
            break

    if header_idx is None:
        return items

    header_row = table[header_idx]
    col_map = {}
    for ci, cell in enumerate(header_row):
        text = (cell or '').replace('\n', ' ')
        for pattern, std_name in COLUMN_MATCHERS:
            if pattern in text:
                col_map[ci] = std_name
                break

    if not col_map:
        return items

    for row in table[header_idx + 1 :]:
        if not row:
            continue
        combined = ''.join(c or '' for c in row).replace('\n', ' ')
        if re.search(r'[小合]\s*计', combined) or '总计' in combined:
            break
        stripped = combined.strip()
        if not stripped or stripped == '.':
            continue

        item = {}
        has_name = False
        for ci, std_name in col_map.items():
            if ci < len(row) and row[ci]:
                val = row[ci].replace('\n', ' ').strip()
                if val and val != '.':
                    item[std_name] = val
                    if std_name == '项目名称':
                        has_name = True
        if has_name:
            # 跳过序号列：如果项目名称全是数字就跳过
            name = item.get('项目名称', '')
            if not re.match(r'^\d+$', name):
                items.append(item)

    return items


# ==================== 主解析函数 ====================


def parse_invoice_text(text, pdf=None):
    """解析普通电子发票文本

    返回:
        dict: { 发票类型, 发票代码, ..., _items: [...] }
    """
    lines = text.split('\n')
    data = {'发票类型': '增值税电子普通发票'}

    # 1. 头部信息（从文本提取）
    data.update(_extract_header_info(text, lines))

    # 2. 主表格（从 PDF 提取）
    table = _find_main_table(pdf)
    if table:
        table_data = _parse_table_data(table)
        for k, v in table_data.items():
            if v or k == '_items':
                data[k] = v

    # 3. 价税合计（备用：如果表格没提取到就从文本找）
    if '价税合计' not in data:
        m = re.search(r'[（(]小写[）)]\s*[¥￥]?\s*([\d,]+\.\d{2})', text)
        if m:
            data['价税合计'] = float(m.group(1).replace(',', ''))
        m = re.search(r'价税合计\s*[（(]大写[）)]\s*(.+?)\s*[（(]小写[）)]', text)
        if m:
            data['价税合计大写'] = m.group(1).strip()

    # 4. 底部收款人/复核/开票人
    data.update(_parse_bottom_info(text))

    # 5. 第二页清单（先试表格，再试文本）
    if pdf and len(pdf.pages) >= 2:
        detail_items = _parse_detail_page(pdf)
        if not detail_items:
            detail_items = _parse_detail_from_text(pdf.pages[1].extract_text() or '')
        if detail_items:
            data['_items'] = detail_items

    return data


# ==================== 文件处理 ====================


def process_pdf(pdf_path):
    """处理单个 PDF 文件，返回 (data_dict, pdf_path)"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''.join(page.extract_text() or '' for page in pdf.pages)
            if not text.strip():
                return {'error': '无法提取文本内容，PDF 可能为扫描件或图片'}, pdf_path
            data = parse_invoice_text(text, pdf)
            data['文件名'] = Path(pdf_path).name
            return data, pdf_path
    except FileNotFoundError:
        return {'error': '文件未找到，请检查文件路径或文件名'}, pdf_path
    except Exception as e:
        err_msg = str(e)
        friendly = '解析失败'
        err_lower = err_msg.lower()
        if 'pdf syntax error' in err_lower or 'pdfsyntaxerror' in err_lower:
            friendly = 'PDF 文件格式损坏或无法解析'
        elif 'password' in err_lower or 'encrypt' in err_lower:
            friendly = 'PDF 文件受密码保护，无法打开'
        elif 'cannot identify image' in err_lower:
            friendly = 'PDF 文件格式损坏或无法解析'
        elif 'permission' in err_lower or 'access denied' in err_lower:
            friendly = 'PDF 文件无权限访问'
        elif 'not a pdf' in err_lower:
            friendly = '文件不是有效的 PDF 格式'
        elif 'out of memory' in err_lower:
            friendly = '文件过大，内存不足无法解析'
        else:
            friendly = f'解析失败：{err_msg[:60]}'
        return {'error': friendly}, pdf_path
