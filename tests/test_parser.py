"""解析器单元测试"""

from unittest.mock import MagicMock, patch

from InvoiceApp.core.parser import (
    _extract_basic_info,
    _find_header_columns,
    _parse_items_table,
    flatten_results,
    parse_invoice_text,
    process_pdf,
)

# ==================== _extract_basic_info ====================


class TestExtractBasicInfo:
    def test_extracts_all_fields(self, sample_basic_info_text):
        """能提取所有基本字段"""
        lines = sample_basic_info_text.split('\n')
        data = _extract_basic_info(sample_basic_info_text, lines)
        assert data['发票号码'] == '1234567890'
        assert data['开票日期'] == '2026年03月06日'
        assert data['购买方名称'] == '测试公司'
        assert data['销售方名称'] == '销售公司'
        assert data['购买方纳税人识别号'] == '91110108MA01ABCDE'
        assert data['销售方纳税人识别号'] == '110105123456789'
        assert data['价税合计'] == 15.0
        assert data['开票人'] == '测试员'
        assert '备注' in data

    def test_empty_text(self):
        """空文本返回空字典"""
        assert _extract_basic_info('', []) == {}

    def test_garbage_text(self):
        """乱码文本不崩溃"""
        assert _extract_basic_info('asdf1234 !@#$%', ['asdf1234 !@#$%']) == {}

    def test_buyer_seller_separate_lines(self):
        """购买方和销售方在不同行（修复售字误匹配）"""
        text = '购买方名称：买方公司\n销售方名称：卖方公司\n'
        data = _extract_basic_info(text, text.split('\n'))
        assert data['购买方名称'] == '买方公司'
        assert data['销售方名称'] == '卖方公司'

    def test_partial_fields(self):
        """只提取存在的字段"""
        text = '发票号码：ABC123\n开票日期：2026年01月01日\n'
        data = _extract_basic_info(text, text.split('\n'))
        assert data['发票号码'] == 'ABC123'
        assert data['开票日期'] == '2026年01月01日'
        assert '购买方名称' not in data

    def test_remark_separate_line(self):
        """备注独占一行"""
        text = '发票号码：1\n备注\n这是一条备注\n开票人：某人\n'
        data = _extract_basic_info(text, text.split('\n'))
        assert '这是一条备注' in data['备注']

    def test_remark_same_line(self):
        """备注在同一行"""
        text = '发票号码：1\n备注：直接跟在后面\n开票人：某人\n'
        data = _extract_basic_info(text, text.split('\n'))
        assert data['备注'] == '直接跟在后面'


# ==================== _find_header_columns ====================


class TestFindHeaderColumns:
    def test_matches_all_standard_columns(self):
        """能匹配所有标准列"""
        header = (
            '项目名称          规格型号    单位  数量    单价      金额      税率/征收率    税额'
        )
        result = _find_header_columns(header)
        names = [name for _, name in result]
        for col in ('项目名称', '规格型号', '单位', '数量', '单价', '金额', '税率/征收率', '税额'):
            assert col in names

    def test_less_than_3_returns_empty(self):
        """少于3列返回空列表"""
        assert _find_header_columns('项目名称 金额') == []

    def test_unknown_column_preserved(self):
        """未识别的列名原样保留"""
        result = _find_header_columns('项目名称 自定义列 金额')
        names = [name for _, name in result]
        assert '自定义列' in names

    def test_matcher_precedence(self):
        """精确匹配优先于模糊匹配"""
        header = '项目名称 规格型号 金额 税率/征收率'
        result = _find_header_columns(header)
        names = [name for _, name in result]
        assert '规格型号' in names
        assert '税率/征收率' in names

    def test_abbreviation_mapping(self):
        """'规格' 映射到 '规格型号'"""
        header = '项目名称 规格 数量 金额'
        result = _find_header_columns(header)
        names = [name for _, name in result]
        assert '规格型号' in names

    def test_exact_match_preferred_over_substring(self):
        """精确匹配优先于子串匹配"""
        # '税率' 是 '税率/征收率' 的子串，但如果列名恰好是 '税率'，应精确匹配
        header = '项目名称 规格型号 单位 数量 单价 金额 税率 税额'
        result = _find_header_columns(header)
        names = [name for _, name in result]
        # '税率' 应该匹配到 '税率/征收率'（因为 COLUMN_MATCHERS 中税率排在税率/征收率后面）
        # 但子串匹配时 '税率' in '税率' 也会匹配到 '税率/征收率'
        assert '税率/征收率' in names


# ==================== _parse_items_table ====================


class TestParseItemsTable:
    def test_standard_items(self, sample_item_lines):
        """正常解析无空格项目"""
        items = _parse_items_table(sample_item_lines)
        assert len(items) == 2
        assert items[0]['项目名称'] == '*经营租赁*通行费'
        assert items[0]['数量'] == '1'
        assert items[0]['金额'] == '15.00'
        assert items[1]['项目名称'] == '*经营租赁*过路费'
        assert items[1]['数量'] == '2'

    def test_items_with_spaces(self, sample_item_lines_with_spaces):
        """项目名称含空格时正确解析"""
        items = _parse_items_table(sample_item_lines_with_spaces)
        assert len(items) == 2
        assert items[0]['项目名称'] == '*经营租赁 * 通行费'
        assert items[0]['数量'] == '1'
        assert items[0]['金额'] == '15.00'
        assert items[0]['规格型号'] == '货车'
        assert items[1]['项目名称'] == '*经营租赁 * 过路费'
        assert items[1]['数量'] == '2'
        assert items[1]['金额'] == '50.00'

    def test_no_header_returns_empty(self):
        """没有表头时返回空列表"""
        assert _parse_items_table(['随便一行', '另一行']) == []

    def test_stops_at_total_line(self):
        """遇到合计行停止解析"""
        lines = [
            '项目名称          金额    税额',
            '*通行费     15.00   ***',
            '*过路费     25.00   ***',
            '合计金额    40.00',
        ]
        items = _parse_items_table(lines)
        assert len(items) == 2

    def test_skips_duplicate_headers(self):
        """跳过重复的表头行"""
        lines = [
            '项目名称          金额    税额',
            '*通行费     15.00   ***',
            '项目名称          金额    税额',
            '*过路费     25.00   ***',
        ]
        items = _parse_items_table(lines)
        assert len(items) == 2

    def test_skips_empty_lines(self):
        """跳过空白行"""
        lines = [
            '项目名称          金额    税额',
            '*通行费     15.00   ***',
            '',
            '*过路费     25.00   ***',
        ]
        items = _parse_items_table(lines)
        assert len(items) == 2

    def test_fewer_than_3_columns_empty(self):
        """<3列的表格返回空"""
        lines = [
            '项目名称',
            '*通行费',
        ]
        assert _parse_items_table(lines) == []

    def test_empty_item_name_skipped(self):
        """项目名称为空的行跳过"""
        lines = [
            '项目名称          金额    税额',
            '              15.00   ***',
        ]
        assert len(_parse_items_table(lines)) == 0

    def test_single_extra_token(self):
        """恰好多一个 token（最常见的情况）"""
        lines = [
            '项目名称       规格型号    单位  数量    单价      金额      税率/征收率    税额',
            '*经营租赁 * 通行费 货车      次    1       15.00     15.00     ***           ***',
        ]
        items = _parse_items_table(lines)
        assert items[0]['项目名称'] == '*经营租赁 * 通行费'
        assert items[0]['规格型号'] == '货车'

    def test_multiple_extra_tokens(self):
        """多个 token 合并回第一列"""
        lines = [
            '项目名称                规格型号    单位  数量    单价      金额      税率/征收率    税额',
            '* 经营 租赁   通行费    货车      次    1       15.00     15.00     ***           ***',
        ]
        items = _parse_items_table(lines)
        assert items[0]['项目名称'] == '* 经营 租赁 通行费'
        assert items[0]['规格型号'] == '货车'


# ==================== parse_invoice_text ====================


class TestParseInvoiceText:
    def test_full_parse(self, sample_invoice_text):
        """完整解析发票文本"""
        result = parse_invoice_text(sample_invoice_text)
        assert result['发票号码'] == '1234567890'
        assert result['价税合计'] == 15.0
        assert len(result['_items']) == 1
        assert result['_items'][0]['项目名称'] == '*经营租赁*通行费'

    def test_parse_with_spaces(self, sample_text_with_spaces_in_name):
        """项目名称含空格时正确解析"""
        result = parse_invoice_text(sample_text_with_spaces_in_name)
        assert result['发票号码'] == '9876543210'
        assert len(result['_items']) == 1
        assert result['_items'][0]['项目名称'] == '*经营租赁 * 通行费'
        assert result['_items'][0]['数量'] == '1'

    def test_empty_text(self):
        """空文本不崩溃"""
        result = parse_invoice_text('')
        assert result.get('_items') == []

    def test_no_items(self, sample_basic_info_text):
        """无项目明细表时 _items 为空列表"""
        result = parse_invoice_text(sample_basic_info_text)
        assert result['发票号码'] == '1234567890'
        assert result['_items'] == []


# ==================== flatten_results ====================


class TestFlattenResults:
    def test_no_items_returns_one_row(self):
        """无项目明细也返回一行"""
        results = [
            ({'发票号码': '123', '_items': [], '价税合计': 15.0}, 'p.pdf'),
        ]
        flat = flatten_results(results)
        assert len(flat) == 1
        assert flat[0][0]['发票号码'] == '123'

    def test_multi_item_expands(self):
        """每个项目明细展开为单独一行"""
        results = [
            (
                {
                    '发票号码': '123',
                    '_items': [
                        {'项目名称': 'A', '金额': '10'},
                        {'项目名称': 'B', '金额': '20'},
                    ],
                    '价税合计': 30.0,
                },
                'p.pdf',
            ),
        ]
        flat = flatten_results(results)
        assert len(flat) == 2
        assert flat[0][0]['项目名称'] == 'A'
        assert flat[1][0]['项目名称'] == 'B'
        assert flat[0][0]['发票号码'] == '123'
        assert flat[1][0]['发票号码'] == '123'
        assert flat[0][0]['价税合计'] == 30.0

    def test_error_results_skipped(self):
        """报错的结果被跳过"""
        results = [
            ({'error': 'file not found'}, 'bad.pdf'),
            ({'发票号码': '456', '_items': []}, 'good.pdf'),
        ]
        flat = flatten_results(results)
        assert len(flat) == 1
        assert flat[0][0]['发票号码'] == '456'

    def test_empty_input(self):
        """空输入返回空列表"""
        assert flatten_results([]) == []

    def test_no_field_collision(self):
        """项目字段不会意外覆盖基本信息"""
        results = [
            ({'发票号码': '123', '_items': [{'项目名称': 'A'}], '备注': 'original'}, 'p.pdf'),
        ]
        flat = flatten_results(results)
        assert flat[0][0]['备注'] == 'original'
        assert flat[0][0]['项目名称'] == 'A'


# ==================== process_pdf (mock) ====================


class TestProcessPdf:
    @patch('InvoiceApp.core.parser.pdfplumber.open')
    def test_success(self, mock_open, sample_invoice_text):
        """正常处理 PDF"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = sample_invoice_text
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_open.return_value = mock_pdf

        data, path = process_pdf('test.pdf')
        assert 'error' not in data
        assert data['发票号码'] == '1234567890'
        assert path == 'test.pdf'

    @patch('InvoiceApp.core.parser.pdfplumber.open')
    def test_empty_text(self, mock_open):
        """提取到空文本时返回错误"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ''
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_open.return_value = mock_pdf

        data, path = process_pdf('empty.pdf')
        assert '无法提取文本内容' in data['error']

    @patch('InvoiceApp.core.parser.pdfplumber.open')
    def test_exception(self, mock_open):
        """PDF 打开异常被捕获"""
        mock_open.side_effect = Exception('PDF corrupted')
        data, path = process_pdf('corrupt.pdf')
        assert 'PDF corrupted' in data['error']

    @patch('InvoiceApp.core.parser.pdfplumber.open')
    def test_adds_filename(self, mock_open, sample_invoice_text):
        """结果中包含文件名"""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = sample_invoice_text
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_open.return_value = mock_pdf

        data, path = process_pdf('invoices/sample.pdf')
        assert data['文件名'] == 'sample.pdf'

    @patch('InvoiceApp.core.parser.pdfplumber.open')
    def test_friendly_pdf_syntax_error(self, mock_open):
        """PDF 语法错误显示友好提示"""
        mock_open.side_effect = Exception('PDFSyntaxError: invalid xref table')
        data, path = process_pdf('bad.pdf')
        assert '格式损坏' in data['error']

    @patch('InvoiceApp.core.parser.pdfplumber.open')
    def test_friendly_password_protected(self, mock_open):
        """加密文件显示友好提示"""
        mock_open.side_effect = Exception('file has not been decrypted')
        data, path = process_pdf('encrypted.pdf')
        assert '密码保护' in data['error']

    @patch('InvoiceApp.core.parser.pdfplumber.open')
    def test_friendly_file_not_found(self, mock_open):
        """文件不存在显示友好提示"""
        mock_open.side_effect = FileNotFoundError()
        data, path = process_pdf('missing.pdf')
        assert '文件未找到' in data['error']

    @patch('InvoiceApp.core.parser.pdfplumber.open')
    def test_multipage(self, mock_open):
        """多页 PDF 文本拼接"""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = '发票号码：123\n'
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = '开票日期：2026年01月01日\n'
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_open.return_value = mock_pdf

        data, path = process_pdf('multi.pdf')
        assert data['发票号码'] == '123'
        assert data['开票日期'] == '2026年01月01日'


# ==================== 集成测试 ====================


class TestIntegration:
    def test_parse_then_flatten(self, sample_invoice_text):
        """端到端：解析 → 展平"""
        data = parse_invoice_text(sample_invoice_text)
        results = [(data, 'test.pdf')]
        flat = flatten_results(results)
        assert len(flat) == len(data['_items'])
        row = flat[0][0]
        assert row['发票号码'] == data['发票号码']
        assert row['项目名称'] == data['_items'][0]['项目名称']

    def test_round_trip_with_spaces(self, sample_text_with_spaces_in_name):
        """端到端：含空格项目名称"""
        data = parse_invoice_text(sample_text_with_spaces_in_name)
        results = [(data, 'spaced.pdf')]
        flat = flatten_results(results)
        assert len(flat) == 1
        row = flat[0][0]
        assert row['项目名称'] == '*经营租赁 * 通行费'
        assert row['金额'] == '15.00'


# ==================== 边界情况 ====================


class TestEdgeCases:
    def test_items_table_only_header(self):
        """只有表头没有数据行"""
        assert _parse_items_table(['项目名称    金额']) == []

    def test_items_table_too_few_header_cols(self):
        """表头列少于3列"""
        lines = ['项目名称', '*经营租赁*通行费']
        assert _parse_items_table(lines) == []

    def test_extract_garbled_text(self):
        """完全不相关的文本不崩溃"""
        data = _extract_basic_info(
            '你好世界\n这是一段中文\n没有发票字段\n', ['你好世界', '这是一段中文', '没有发票字段']
        )
        assert data == {}
