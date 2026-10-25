"""실제 Chrome/file:// 통합 시험. python3 -m unittest discover -s tests -p 'test_*.py' -v
개발용 의존성: Python playwright + 로컬 Google Chrome. 앱에는 의존성 없음.
"""
import io
import json
import os
from pathlib import Path
import sys
import unittest
import zipfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import validate_drafts as reference

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML = f'''<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>계약 &amp; 자문</w:t><w:tab/><w:t>보수</w:t><w:br/><w:t>둘째 줄</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>첫 칸</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>둘째 칸</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'''

def docx(xml=XML, compression=zipfile.ZIP_DEFLATED, name='word/document.xml'):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=compression) as z:
        z.writestr('[Content_Types].xml', '<Types/>')
        z.writestr(name, xml)
    return out.getvalue()

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel='chrome', timeout=20000)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.set_default_timeout(4000)
        self.errors, self.network = [], []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.on('request', lambda r: self.network.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
        self.page.goto((ROOT / 'index.html').as_uri())

    def tearDown(self):
        self.page.close()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.network, [], '초안을 네트워크로 보내면 안 됩니다')

    def upload(self, name, data):
        self.assertEqual(self.page.locator('#draft-file').count(), 1, '파일 선택 UI 필요')
        self.page.locator('#draft-file').set_input_files({'name': name, 'mimeType': 'application/octet-stream', 'buffer': data})
        self.page.wait_for_function("document.querySelector('#file-status').textContent && !document.querySelector('#file-status').textContent.includes('읽는 중')")

    def test_11_screen_results_match_python(self):
        paths = sorted((ROOT / 'data/drafts').glob('*.md')) + [ROOT / f'data/ai_compare/{n}.md' for n in ('claude', 'gemini', 'codex')]
        self.assertEqual(len(paths), 11)
        self.assertEqual(self.page.locator('#sample option').count(), 12)
        rows = []
        standards = reference.load_standard()
        titles = {'🔴': '서명 보류', '🟡': '검토 후 진행', '🟢': '진행 가능'}
        for i, path in enumerate(paths):
            with self.subTest(draft=path.stem):
                text = path.read_text(encoding='utf-8')
                codes, detail = reference.review(text)
                verdict = reference.verdict(codes)
                self.page.select_option('#sample', str(i))
                self.assertEqual(self.page.input_value('#draft'), text)
                self.page.locator('button[type=submit]').click()
                actual = self.page.locator('#findings > li').evaluate_all('(els)=>els.map(e=>e.dataset.code)')
                self.assertEqual(actual, [c.split('×')[0] for c in codes])
                self.assertEqual(self.page.locator('#verdict h2').inner_text(), titles[verdict])
                for code in actual:
                    item = self.page.locator(f'#findings > li[data-code="{code}"]')
                    self.assertEqual(item.locator('.recommendation strong').inner_text(), '검토된 표준 문구')
                    self.assertEqual(item.locator('.recommendation span').text_content(), standards[code])
                    if code.startswith('R'):
                        expected_hits = [d.split(': ', 1)[1] for d in detail if d.startswith(f'⚠ {code} ')]
                        self.assertEqual(item.locator('.evidence').all_text_contents(), expected_hits)
                    elif code == 'BLANK':
                        self.assertEqual(item.locator('.evidence').all_text_contents(), reference.BLANK.findall(text))
                js = self.page.evaluate('(t)=>review(t)', text)
                self.assertEqual(js['detail'], detail)
                rows.append({'name': path.stem, 'python': codes, 'screen': codes, 'verdict': titles[verdict], 'match': True})
        if os.environ.get('VERIFY_OUTPUT'):
            Path(os.environ['VERIFY_OUTPUT']).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')

    def test_txt_md_and_utf16(self):
        for name, data, expected in [('초안.TXT', '첫 줄\n둘째 줄'.encode(), '첫 줄\n둘째 줄'), ('초안.md', b'\xef\xbb\xbf# title\nbody', '# title\nbody'), ('word.txt', '한글 문서'.encode('utf-16'), '한글 문서')]:
            with self.subTest(name=name):
                self.upload(name, data)
                self.assertEqual(self.page.input_value('#draft'), expected)
                self.assertEqual(self.page.input_value('#sample'), '')

    def test_docx_compressed_and_stored(self):
        for compression in (zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED):
            with self.subTest(compression=compression):
                self.upload('계약.docx', docx(compression=compression))
                self.assertEqual(self.page.input_value('#draft'), '계약 & 자문\t보수\n둘째 줄\n첫 칸\n둘째 칸')

    def test_invalid_files_preserve_input(self):
        malformed = docx(xml='<not-valid>')
        encrypted = bytearray(docx())
        pos = encrypted.index(b'PK\x01\x02', encrypted.index(b'PK\x01\x02') + 1)
        encrypted[pos + 8] |= 1
        cases = [('a.pdf', b'%PDF'), ('a.doc', b'old'), ('a.docx', b'bad zip'), ('a.docx', docx(name='missing.xml')), ('a.docx', malformed), ('a.docx', bytes(encrypted)), ('empty.txt', b''), ('a.txt', b'\xff\x00\x81'), ('a.txt', b'a' * (10 * 1024 * 1024 + 1))]
        for name, data in cases:
            with self.subTest(name=name, size=len(data)):
                self.page.fill('#draft', '기존 초안 보존')
                self.upload(name, data)
                self.assertEqual(self.page.input_value('#draft'), '기존 초안 보존')
                self.assertTrue(self.page.locator('#file-status').evaluate("e=>e.classList.contains('error')"))

    def test_docx_automatic_lists_preserve_negation(self):
        for inherited in (False, True):
            with self.subTest(inherited=inherited):
                prop = '<w:pStyle w:val="ListNumber"/>' if inherited else '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
                paragraphs = '<w:p><w:r><w:t>다음 업무는 포함하지 않는다.</w:t></w:r></w:p>'
                for text in ('금융기관 알선', '투자 중개'):
                    paragraphs += f'<w:p><w:pPr>{prop}</w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'
                xml = f'<w:document xmlns:w="{W}"><w:body>{paragraphs}</w:body></w:document>'
                stream = io.BytesIO(docx(xml=xml))
                with zipfile.ZipFile(stream, 'a') as z:
                    z.writestr('word/styles.xml', f'<w:styles xmlns:w="{W}"><w:style w:styleId="ListNumber"><w:pPr><w:numPr><w:numId w:val="1"/></w:numPr></w:pPr></w:style></w:styles>')
                    z.writestr('word/numbering.xml', f'<w:numbering xmlns:w="{W}"><w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum><w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>')
                self.upload('목록.docx', stream.getvalue())
                text = self.page.input_value('#draft')
                self.assertEqual(text, '다음 업무는 포함하지 않는다.\n1. 금융기관 알선\n2. 투자 중개')
                result = self.page.evaluate('(t)=>review(t)', text)
                self.assertNotIn('R2', result['codes'])
                self.assertNotIn('C1', result['codes'])

    def test_docx_uncompressed_size_limit(self):
        self.page.fill('#draft', '기존 초안')
        self.upload('huge.docx', docx(xml='a' * (10 * 1024 * 1024 + 1)))
        self.assertEqual(self.page.input_value('#draft'), '기존 초안')
        self.assertIn('10 MB', self.page.locator('#file-status').inner_text())

    def test_show_three_then_expand(self):
        self.page.fill('#draft', '\n'.join(f'성공보수 {i}를 지급한다.' for i in range(5)))
        self.page.locator('button[type=submit]').click()
        item = self.page.locator('[data-code=R4]')
        self.assertEqual(item.locator('.evidence:visible').count(), 3)
        self.assertEqual(item.locator('summary').inner_text(), '외 2곳')
        item.locator('summary').click()
        self.assertEqual(item.locator('.evidence:visible').count(), 5)
        item.locator('summary').click()
        self.assertEqual(item.locator('.evidence:visible').count(), 3)

    def test_slow_read_does_not_overwrite_new_input(self):
        self.assertEqual(self.page.locator('#draft-file').count(), 1)
        self.page.evaluate("() => {window.originalRead=readDraftFile; readDraftFile=()=>new Promise(r=>window.finishRead=r);}")
        self.page.locator('#draft-file').set_input_files({'name': 'slow.txt', 'mimeType': 'text/plain', 'buffer': b'old'})
        self.page.select_option('#sample', '0')
        current = self.page.input_value('#draft')
        self.page.evaluate("window.finishRead('늦게 도착한 텍스트')")
        self.assertEqual(self.page.input_value('#draft'), current)
        self.assertNotIn('읽는 중', self.page.locator('#file-status').inner_text())

    def test_safe_text_and_result_invalidation(self):
        text = '<img src=x onerror=alert(1)> 성공보수를 지급한다.'
        self.upload('safe.txt', text.encode())
        self.page.locator('button[type=submit]').click()
        self.assertEqual(self.page.locator('#findings img').count(), 0)
        self.assertIn(text, self.page.locator('#findings').inner_text())
        self.upload('next.md', b'new draft')
        self.assertTrue(self.page.locator('#results').is_hidden())
        self.page.fill('#draft', '')
        self.page.locator('button[type=submit]').click()
        self.assertTrue(self.page.locator('#input-error').is_visible())

    def test_mobile_layout(self):
        self.page.set_viewport_size({'width': 390, 'height': 844})
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))

if __name__ == '__main__':
    unittest.main()
