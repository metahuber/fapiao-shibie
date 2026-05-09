"""发票解析工厂 — 自动识别发票类型并分派到对应解析器"""

from . import parser as parser_shudian
from . import parser_normal


def detect_invoice_type(text):
    """根据文本内容自动识别发票类型

    返回: 'normal' (增值税电子普通发票) 或 'shudian' (数电发票)
    """
    if '增值税电子普通发票' in text:
        return 'normal'
    # 数电发票特征：没有"增值税电子普通发票"字样，
    # 但包含数电票的典型字段如 "发票号码"+"项目名称" 等
    if '项目名称' in text or '价税合计' in text:
        return 'shudian'
    # 默认当成数电发票处理
    return 'shudian'


def process_pdf(pdf_path):
    """处理单个PDF文件，自动识别发票类型并解析

    返回: (data_dict, pdf_path)
    """
    from pathlib import Path

    import pdfplumber

    fname = Path(pdf_path).name
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ''.join(page.extract_text() or '' for page in pdf.pages)
            if not text.strip():
                return {
                    'error': '无法提取文本内容，PDF 可能为扫描件或图片',
                    '文件名': fname,
                }, pdf_path
            invoice_type = detect_invoice_type(text)

            if invoice_type == 'normal':
                data = parser_normal.parse_invoice_text(text, pdf)
            else:
                data = parser_shudian.parse_invoice_text(text)

            data['文件名'] = fname
            return data, pdf_path
    except FileNotFoundError:
        return {'error': '文件未找到，请检查文件路径或文件名', '文件名': fname}, pdf_path
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
        return {'error': friendly, '文件名': fname}, pdf_path
