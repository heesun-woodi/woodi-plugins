# synthetic-qual-research

목표 하나에서 의사결정까지, 합성사용자(`nvidia/Nemotron-Personas-Korea`, 1M 한국 성인 페르소나)
대상 **정성조사 전 과정**을 지휘하는 오케스트레이터 플러그인.

## 번들된 스킬 (3)

| 스킬 | 역할 |
|---|---|
| **synthetic-qual-research** | 컨덕터. 목표 → 설문 → 필드 → ICP → 심층인터뷰 → 종합. 런 디렉토리·재현성 매니페스트·UUID 파일-용접·휴먼 게이트 2개·타당성 캡션을 소유 |
| **backward-survey-builder** | 합성 응답자용 backward-design 설문 설계 (목표→RQ→태그 문항) |
| **synthetic-icp-interview** | 설문 필드 → 근거 기반 ICP 선정 → in-character 심층인터뷰 |

## 트리거

- 전체 아크(목표→의사결정): `"합성사용자 조사 통째로"`, `"목표부터 의사결정까지 조사해줘"`, `"end-to-end synthetic qual research"`
- 설문만: `backward-survey-builder`
- 설문 있고 필드+인터뷰만: `synthetic-icp-interview`

## 의존성 (중요)

이 플러그인은 **얇은 오케스트레이터**라 아래가 있어야 완전히 동작합니다:

1. **`nemotron-personas-korea` 플러그인** (같은 마켓플레이스) — `persona-respondent` 에이전트,
   `/persona-interviewee` 커맨드, 데이터셋 로더(`load_persona.py`), `dispatch-strategy`,
   `synthetic-population-validity`. **먼저 설치하세요.**
2. **로컬 Python 환경** — `datasets` + `pandas`.
3. **데이터셋 캐시(~5.76GB)** — `HF_HOME` 아래. Phase 2(draw·필드)가 실제 데이터셋을 읽습니다.

> 위 2·3이 없는 샌드박스 환경에서는 설계(Phase 1)·인터뷰 연기·종합 같은 텍스트 단계는 되지만,
> 실제 페르소나 draw·필드(Phase 2)는 돌지 않습니다.

## 번들 스크립트 (v2)

- `skills/synthetic-qual-research/scripts/draw_personas.py` — N명 배치 draw(재현성). `load_persona.py`는
  1행만 뽑으므로 이 헬퍼가 N행을 담당.
- `skills/synthetic-qual-research/scripts/validate_results.py` — UUID 불변식 + 응답 스키마 게이트
  (exit 0 통과 / 2 하드스톱(지어낸 uuid) / 3 재디스패치 슬롯 목록).

## 산출물

런마다 `${SQR_RUNS_DIR:-research/runs}/<날짜>-<slug>/`에 `manifest.json`, `survey.md`,
`drawn_personas.jsonl`, `results.json`, `icp.json`, `transcript-*.md`, `synthesis.md`를 남깁니다.
`phase_status`로 중단 런 재개 가능.
