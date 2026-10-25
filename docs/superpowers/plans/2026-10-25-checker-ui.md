# 계초기 점검 화면 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. 사용자 요청에 따라 직접 구현하며 커밋은 사용자 확인 후에만 한다.

**Goal:** 단일 index.html에서 초안을 점검하고 판정·근거·권장 문구를 보여 준다.
**Architecture:** 원본 규칙 문서와 권장 문구 문서 및 시험 초안 8건을 JSON으로 HTML 안에 보존한다. 기준 Python 구현과 같은 순서·정규식으로 JavaScript 점검 함수를 구현하고 DOM은 textContent로 작성한다.
**Tech Stack:** HTML, CSS, JavaScript, Python/Node 검증 도구(개발용).
**Spec:** AGENTS.md, rules/review_rules.md, rules/standard_clauses.md, 사용자 승인 범위.

## Global Constraints
- 외부 라이브러리·서버·API 호출 없이 file://에서 동작.
- 원본 문서와 초안은 수정하지 않고 그대로 내장.
- 입력은 전송·저장하지 않는다. 법률 판단이 아닌 참고용 안내를 항상 결과에 표시.
- feat/checker-ui에서 작업하며 커밋·푸시는 하지 않는다.

## Review Focus
- 빈 입력은 진행 가능으로 판정하지 않고 입력 안내.
- HTML 같은 입력은 코드가 아닌 텍스트로 표시.
- 입력 수정/시험 초안 전환 시 이전 결과를 숨겨 오해 방지.
- 모바일 화면에서 가로 넘침 없이 사용.
- 부정문, 제목, 소개 자료/소개서 제외 규칙은 Python과 동일.

## Task 1: 화면과 검증
**Files:** index.html 생성, tests/checker.test.cjs 생성, README.md 실행/기록 갱신.
**Interfaces:** review(text) → {codes, detail, verdict, findings}; SOURCE → {rules, standard, drafts:[{name,text}]}; STANDARD → 코드별 원문 권장 문구.
- [x] Node 내장 테스트로 원본 내장 일치와 8건의 Python 대비 결과·상세·판정 일치 검사를 먼저 작성하고 실패 확인.
- [x] index.html에 입력, 샘플 선택, 점검 버튼, 결과와 권장 문구 구현.
- [x] Node 테스트 및 python3 validate_drafts.py 실행. 모두 일치해야 통과.
- [x] 실제 브라우저에서 8건의 선택/점검 결과를 수집하고 파일로 보존, 결과 표 생성. 빈 입력/텍스트 안전 표시/결과 초기화/모바일 확인.
- [x] README 기록 갱신 후 브라우저를 열어 사용자 확인 요청. 커밋 보류.
