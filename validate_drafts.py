"""외부 AI가 쓴 자문 계약서 초안을 점검 규칙(rules/review_rules.md)으로 검사합니다.

실행:
  python3 validate_drafts.py              # data/drafts/ 시험 초안 8건을 점검하고 정답과 비교
  python3 validate_drafts.py 내초안.md     # 파일 하나를 점검해 결과만 출력
MVP 화면의 점검 결과가 이 출력과 같으면 규칙이 맞게 구현된 것입니다.
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
DRAFTS = BASE / "data" / "drafts"
AI_DRAFTS = BASE / "data" / "ai_compare"
STANDARD = BASE / "rules" / "standard_clauses.md"

# A. 위험 표현 (⚠ 경고) — 부정·면제 문장은 제외
NEGATION = re.compile(r"아니|않|아님|관계없이|무관|상관없이|여부와\s*별도")
RISK = {
    "R1": ("성과 연동 보수", re.compile(r"보수|수수료|자문료"), re.compile(r"(대출|투자|자금\s*조달|조달)\S{0,3}\s*(실행|승인|약정|유치|성사|성공|완료|확정)|대출금|투자금|조달금액")),
    "R2": ("중개성 표현", None, re.compile(r"알선|주선|중개|소개(?!\s*자료|서)")),
    "R4": ("'성공보수·성과보수' 표현", None, re.compile(r"성공\s*보수|성과\s*보수")),
    "R3": ("성사 보장 표현", re.compile(r"대출|투자|조달|승인|성사|유치"), re.compile(r"보장|확약|책임지고")),
}

# B. 필수 조항 (✕ 없으면 오류)
REQUIRED = {
    "C1": ("중개 금지(자문 한정) 조항", lambda s: re.search(r"중개|알선|주선", s) and re.search(r"아니|않", s)),
    "C2": ("성사 여부와 무관한 보수 지급 조항", lambda s: re.search(r"관계없이|무관하게|상관없이|여부와\s*별도", s) and re.search(r"성사|실행|조달|유치|성공", s)),
    "C3": ("업무 범위 조항", lambda s: re.search(r"업무 범위|업무의 범위", s)),
    "C4": ("보수와 지급 조항", lambda s: re.search(r"보수|자문료", s) and "지급" in s),
    "C5": ("비밀유지 조항", lambda s: "비밀" in s),
    "C6": ("면책 조항 (자문은 의견, 최종 판단 책임은 의뢰인)", lambda s: re.search(r"최종\s*(적인\s*)?(의사결정|판단)|판단으로 인하여", s) and re.search(r"책임", s)),
    "C7": ("계약 해지 조항", lambda s: "해지" in s),
    "C8": ("관할 조항", lambda s: "관할" in s),
    "C9": ("손해배상 한도 조항 (받은 보수 총액 한도)", lambda s: re.search(r"한도", s) and re.search(r"보수", s) and re.search(r"배상|책임", s)),
}

# C. 빈칸·미완성 (✕)
BLANK = re.compile(r"○+|O{2,}|X{3,}|_{2,}|(?<!조 )\[(?!\s*(?:별첨|별표|붙임)\s*\])[^\]]*\]|\{\{[^}]*\}\}")

EXPECTED = {
    "draft_01_정상": [],
    "draft_02_성과연동보수": ["R1", "R4", "C2"],
    "draft_03_알선표현": ["R2", "C1"],
    "draft_04_빈칸": ["BLANK×4"],
    "draft_05_보장표현": ["R3"],
    "draft_06_조항누락": ["C5", "C7"],
    "draft_07_부정문정상": [],
    "draft_08_복합": ["R1", "R2", "R4", "BLANK×1", "C6", "C9"],
}


EXPECTED_VERDICT = {
    "draft_01_정상": "🟢", "draft_02_성과연동보수": "🔴", "draft_03_알선표현": "🔴", "draft_04_빈칸": "🔴",
    "draft_05_보장표현": "🟡", "draft_06_조항누락": "🔴", "draft_07_부정문정상": "🟢", "draft_08_복합": "🔴",
}
# 실제 AI 초안 회귀 시험 (data/ai_compare/) — 규칙을 고친 뒤에도 결과가 유지되는지 확인
EXPECTED_AI = {
    "claude": ["R1", "R4", "BLANK×3"],
    "gemini": ["R1", "R2", "R4", "BLANK×20", "C1", "C2"],
    "codex": ["R1", "R4", "BLANK×14", "C6", "C9"],
}
VERDICT_TEXT = {"🔴": "서명 보류 — ✕ 오류를 먼저 고치세요", "🟡": "검토 후 진행 — ⚠ 경고 문장을 사람이 확인하세요", "🟢": "진행 가능 — 그래도 서명 전 최종 확인은 사람이 합니다"}


def verdict(codes):
    """✕(필수 조항 누락·빈칸)가 하나라도 있으면 🔴, ⚠(위험 표현)만 있으면 🟡, 없으면 🟢"""
    if any(c.startswith("C") or c.startswith("BLANK") for c in codes):
        return "🔴"
    return "🟡" if codes else "🟢"


def load_standard():
    """standard_clauses.md 에서 코드별 '권장:' 문구를 읽습니다."""
    out, code = {}, None
    for line in STANDARD.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            code = line[4:].strip()
        elif code and line.startswith("- 권장: "):
            out[code] = line[len("- 권장: "):]
    return out


def sentences(text, headings=False):
    """문장 단위로 나눕니다. 위험 표현은 본문만, 필수 조항은 조 제목까지 포함해 찾습니다."""
    parts = re.split(r"\n+|(?<=다\.)\s+", text)
    return [p.strip() for p in parts if p.strip() and (headings or not p.startswith("#"))]


def negated_items(sents):
    """'다음 업무는 포함하지 않는다' 같은 부정 문장 바로 아래의 번호 목록(1. 2. …)은 부정된 것으로 봅니다."""
    out, block = set(), False
    for i, s in enumerate(sents):
        if re.match(r"^\d+\.", s):
            if block:
                out.add(i)
            continue
        block = bool(NEGATION.search(s) and "다음" in s)
    return out


def review(text):
    """초안 텍스트를 점검해 (코드 목록, 상세 내용) 을 돌려줍니다."""
    sents = sentences(text)
    negated = negated_items(sents)
    codes, detail = [], []
    for code, (name, need, pat) in RISK.items():
        hits = [s for i, s in enumerate(sents) if pat.search(s) and not NEGATION.search(s) and i not in negated and (need is None or need.search(s))]
        if hits:
            codes.append(code)
            detail += [f"⚠ {code} {name}: {h}" for h in hits]
    blanks = BLANK.findall(text)
    if blanks:
        codes.append(f"BLANK×{len(blanks)}")
        detail.append(f"✕ 빈칸 {len(blanks)}곳: {', '.join(blanks)}")
    for code, (name, found) in REQUIRED.items():
        listed = code == "C1" and any(re.search(r"중개|알선|주선", sents[i]) for i in negated)
        if not listed and not any(found(s) for s in sentences(text, headings=True)):
            codes.append(code)
            detail.append(f"✕ {code} {name} 없음")
    return codes, detail


def main():
    if len(sys.argv) > 1:
        codes, detail = review(Path(sys.argv[1]).read_text(encoding="utf-8"))
        v = verdict(codes)
        print(f"종합 판정: {v} {VERDICT_TEXT[v]}")
        print("\n".join(detail) or "문제 없음")
        std = load_standard()
        shown = {c.split("×")[0] for c in codes}
        if shown:
            print("\n권장 표준 문구 (rules/standard_clauses.md)")
            for c in sorted(shown):
                print(f"- {c}: {std.get(c, '(문구 없음)')}")
        return
    mismatch = []
    for path in sorted(DRAFTS.glob("*.md")):
        codes, detail = review(path.read_text(encoding="utf-8"))
        v = verdict(codes)
        print(f"{v} {path.stem}: {', '.join(codes) or '문제 없음'}")
        if sorted(codes) != sorted(EXPECTED.get(path.stem, ["(정답 없음)"])) or v != EXPECTED_VERDICT.get(path.stem):
            mismatch.append((path.stem, EXPECTED.get(path.stem), codes))
    for name, exp in EXPECTED_AI.items():
        path = AI_DRAFTS / f"{name}.md"
        if not path.exists():
            continue
        codes, _ = review(path.read_text(encoding="utf-8"))
        print(f"{verdict(codes)} AI·{name}: {', '.join(codes) or '문제 없음'}")
        if sorted(codes) != sorted(exp):
            mismatch.append((f"AI·{name}", exp, codes))
    std = load_standard()
    missing = [c for c in [*RISK, *REQUIRED, "BLANK"] if c not in std]
    print("권장 문구가 없는 코드:", missing or "없음")
    print("정답과 불일치:", mismatch or "없음")


if __name__ == "__main__":
    main()
