# Rules v2 + local file upload Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. 사용자 승인 범위에 따라 현재 feat/rules-v2-upload에서 구현하며 커밋은 사용자 화면 확인 이후에만 한다.

**Goal:** v2 규칙과 11건 초안을 화면에 일치시키고 로컬 TXT/MD/DOCX 입력을 지원한다.
**Architecture:** 기존 단일 index.html에 원본 데이터와 Python 대응 점검 함수를 내장한다. DOCX는 ZIP 중앙 디렉터리에서 word/document.xml을 찾아 브라우저 DecompressionStream과 DOMParser로 본문만 추출한다.
**Tech Stack:** HTML/CSS/JavaScript, Python 표준 라이브러리, Node test, 실제 Chromium 검증.
**Spec:** docs/변경안_v2.md 및 사용자 승인 메시지.

## Global Constraints
- 외부 런타임 라이브러리·서버·전송·저장 없음. file:// 실행 유지.
- TXT·MD·DOCX만 지원하며 PDF는 거절한다.
- 기준 스크립트와 규칙·표준 문구·초안은 제공 파일 그대로 복사한다.
- 시험 8건 + Claude/Gemini/Codex 3건의 코드·상세·판정 모두 Python과 같아야 한다.
- AGENTS.md의 파일 정책과 필수 조항 9종을 수정한다.
- 커밋·푸시하지 않는다.

## Review Focus
- 손상되거나 암호화된 DOCX: 오류를 표시하고 기존 입력을 보존한다.
- 압축 폭탄·대용량 입력: 파일/본문 한도로 메모리 사용을 제한한다.
- DOCX 문단·표·탭·줄바꿈·XML 특수문자: 텍스트 순서와 경계 보존.
- 비동기 파일 읽기 중 다른 초안 선택: 최신 사용자 입력을 덮어쓰지 않는다.
- 위험 문장에 HTML 삽입: 실행하지 않고 텍스트로 표시한다.

## Task 1: v2 규칙/데이터 일치
Files: validate_drafts.py, rules/, data/, docs/변경안_v2.md, index.html, tests/checker.test.cjs, AGENTS.md.
Interfaces: review(text) -> {codes, detail, verdict, findings}; SOURCE.drafts에 11건 내장.
- [ ] 11건 정답과 v2 경계 조건 테스트 추가, 기존 구현에서 실패 확인.
- [ ] 제공 파일 복사, AGENTS 지침 갱신, Python과 같은 순서/정규식/부정 목록 처리 구현.
- [ ] node --test tests/checker.test.cjs 및 python3 validate_drafts.py 실행: 불일치 없음.

## Task 2: 로컬 파일 입력과 화면
Files: index.html, tests/browser.test.cjs.
Interfaces: readDraftFile(file) -> Promise<string>; ZIP/XML 추출은 브라우저 기본 API 사용.
- [ ] 실제 브라우저 테스트 작성: TXT/MD, stored/deflated DOCX, 문단/표/탭, 지원 외 형식, 손상/암호화/과대 파일, 늦은 읽기, HTML 안전성, 펼치기.
- [ ] 기존 화면에서 신규 기능 테스트 실패 확인.
- [ ] 업로드 입력과 접근성 상태/오류 표시, stale read 차단, 3문장+외 N곳 details, 검토된 표준 문구 표시 구현.
- [ ] 전체 Node/브라우저 테스트 통과 및 네트워크 전송 0건 확인.

## Task 3: 검증과 사용자 인계
Files: README.md, docs/v2-verification.md.
Interfaces: Python 기준 결과와 실제 DOM 결과 비교표 11행.
- [ ] 11건 모두 실제 화면에서 불러오기·점검, 코드/문장/문구/판정 비교.
- [ ] 독립 리뷰 후 중요 오류 수정, 전체 테스트 재실행.
- [ ] README 작업 기록과 검증 문서 갱신; 브라우저로 index.html 열기.
- [ ] git diff --check 및 상태 확인; 커밋 없이 사용자 확인 요청.
