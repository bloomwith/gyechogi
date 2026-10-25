"""원본 규칙/표준 문구/11개 초안을 단일 HTML의 데이터 블록으로 동기화."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    drafts = sorted((ROOT / 'data/drafts').glob('*.md'))
    assert len(drafts) == 8
    drafts += [ROOT / f'data/ai_compare/{name}.md' for name in ('claude', 'gemini', 'codex')]
    source = {
        'rules': (ROOT / 'rules/review_rules.md').read_text(encoding='utf-8'),
        'standard': (ROOT / 'rules/standard_clauses.md').read_text(encoding='utf-8'),
        'drafts': [{'name': p.stem, 'text': p.read_text(encoding='utf-8')} for p in drafts],
    }
    file = ROOT / 'index.html'
    html = file.read_text(encoding='utf-8')
    start = '<script id="source-data" type="application/json">'
    before, rest = html.split(start, 1)
    _, after = rest.split('</script>', 1)
    # HTML parser가 데이터 안의 닫는 script를 태그로 해석하지 않게 한다.
    data = json.dumps(source, ensure_ascii=False).replace('<', '\\u003c')
    file.write_text(before + start + data + '</script>' + after, encoding='utf-8')
    print(f'원본 데이터 {len(drafts)}건 동기화')

if __name__ == '__main__':
    main()
