---
description: 클라크 학원 블로그 글 한 편을 주제 리서치부터 네이버 임시저장까지 진행합니다(게이트 3개·에이전트 2개·lint·업로드).
argument-hint: "[주제 번호 또는 'report NNN' (선택)]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Skill, Agent, SendMessage, AskUserQuestion
---

사용자(이랑)가 클라크 블로그 글 작업을 시작했다. 너(메인 세션)는 **오케스트레이터**다. 아래 순서대로 글 **한 편**을 진행하라.
사용자에게 보여주는 모든 안내 문구는 **한국어**로 쓴다. 비밀번호·API 키 값·세션 파일 내용은 출력하지 않는다.

인자: `$ARGUMENTS`
- 비어 있음 → Step 0부터 전체 진행.
- 숫자(예: `3`) → 주제 번호. 오늘 날짜 topics 파일이 있으면 Step 1 리서치를 건너뛰고 게이트 1에서 이 번호를 기본값으로 쓴다.
- `report NNN` → 맨 아래 "report NNN" 절만 수행하고 끝낸다(preflight·디스패치·파일 쓰기 없음).
- `resume NNN` → 맨 아래 "resume NNN" 절만 수행한다(멈춘 곳부터 이어서 — `final.md`가 있으면 Step 5 업로드만(세션이 없어 업로드를 미뤘을 때), 없고 `draft-v2.md`·`## 초안피드백`이 있으면 Step 3 이미지부터(키·실사진이 없어 멈췄을 때)).

---

## 운영 원칙 (모든 단계에 적용)

- **cwd = 작업 폴더**(`knowledge/`·`scripts/`·`work/`가 있는 폴더). 모든 경로는 작업 폴더 기준. 글 폴더는 `work/posts/<NNN-slug>/`(아래에서 `P`).
- **메인만 하는 일**: 사용자 게이트 3개(AskUserQuestion), `P/gates.md` 기록, 주제 리서치(Step 1)·이미지(Step 3)·`final.md` 작성(Step 4)·업로드(Step 5), `work/variation-log.md` 기록.
- **서브에이전트는 2개뿐**이고 플러그인 네임스페이스로 부른다: `clark-blog:blog-writer`(B·B'), `clark-blog:blog-fact-checker`(C). model은 넘기지 않는다(에이전트 정의의 `opus`).
  발주 프롬프트에는 **경로만** 넣는다(내용을 붙여넣지 않는다). 절차 스킬은 `${CLAUDE_PLUGIN_ROOT}`가 펼쳐진 **절대경로** 그대로 넣는다.
- **서브에이전트는 사용자에게 묻지 않는다.** 질문은 반환 메시지·`factcheck.md`·`seo.md`의 `## 질문`(또는 "메인에 전달") 절로 돌아온다 → 메인이 AskUserQuestion으로 이랑에게 묻고, 답을 `gates.md`에 기록한 뒤 다음 발주·재개 메시지에 원문으로 넣는다.
- **재개는 `name` + `SendMessage`**: writer는 `blog-writer-<NNN>` 하나를 B부터 끝까지 재개한다(새 Agent로 다시 만들지 않는다). fact-checker는 회차마다 새 Agent `blog-fact-checker-<NNN>-r<k>`(r1, r2).
  `SendMessage`가 실패하면(세션이 바뀌어 에이전트가 없음) 같은 `subagent_type`·같은 `name`으로 새 Agent를 발주하고 B 입력 경로 전부 + B' 메시지를 함께 넣는다(디스패치 1회로 센다).
- **디스패치 예산**: 글 1편당 기본 3회(B·C·B'), 재작업 포함 **최대 7회**(B·C·B'·lint 재개 B'·게이트 2 B'·C r2·r2 반영 B'). Agent 발주와 SendMessage 재개를 모두 1회로 센다. 다음 디스패치가 8회째면 **하지 말고 멈춰서** 이랑에게 보고한다(지금까지 횟수·남은 문제·글 폴더 경로). Step 4 lint 텍스트 FAIL → B' 재개(및 Step 5 exit 10·11의 B' 재개)도 1회로 센다 — 최악 경로에서 이것이 8회째면 하지 않고 중단·보고. 매 디스패치 뒤 `디스패치 n/7`을 한 줄로 알린다.
- **완료 확인**: 에이전트가 끝났다고 해도 출력 파일이 실제로 있는지 `ls`로 확인한다. 없으면 같은 에이전트를 1회 재개(예산 포함)하고, 그래도 없으면 멈추고 보고한다.
- **gates.md 절은 4개로 고정**: `## 선택` · `## 초안피드백` · `## 이미지승인` · `## 업로드`. 다른 절을 만들지 않는다. 절 단위로 **append**하고, 같은 절이 둘 이상이면 **마지막 것이 유효**하다. 각 절 첫 줄은 `- 일시: YYYY-MM-DD HH:MM`.
- **에러 시 중단·보고**: 예상 밖 오류(스크립트 exit 2, 파일 없음, 요약 줄 없음 등)는 우회하지 말고 멈춘 뒤 단계·명령·출력 첫 줄·글 폴더를 보고한다. 같은 오류 재시도는 한 번까지.
- 메인은 `draft.md`·`draft-v2.md`·`factcheck*.md`·`research.md`·`seo.md`를 고치지 않는다(예외: B' 생략 규칙의 `cp draft.md draft-v2.md` 한 번).
- **미검증 사실 변경**: writer 반환의 "사실 문장 변경"이 `없음`이 아니면 그 문장은 fact-checker가 보지 않은 것이다. 게이트 2 전에 생긴 것은 게이트 2 수정 루프의 C r2에서 검토한다. C r2 반영 B'가 다시 "사실 문장 변경"을 보고하거나, 게이트 2 이후(Step 4·5의 B' 재개)에 생기면 r3를 발주하지 않고, 바뀐 문장을 이랑에게 보여 주며 AskUserQuestion `이대로 진행` / `여기서 중단`.

---

## Step 0. preflight

한 번의 Bash 호출로 확인한다. 키 값은 출력하지 않는다. `naver-blog-cli`는 종료 코드가 항상 0이므로 **stdout 문구**(`세션 정상` + `글쓰기 가능`)로 판정한다.

```bash
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
echo "작업 폴더: $PWD"
[ -d knowledge ] && [ -d scripts ] && echo "work-folder: OK" || echo "work-folder: MISSING"
if [ -n "$GEMINI_API_KEY" ]; then echo "GEMINI_API_KEY: env에 있음"
elif [ -f .env ] && grep -q '^GEMINI_API_KEY=.' .env; then echo "GEMINI_API_KEY: .env에 있음"
else echo "GEMINI_API_KEY: MISSING"; fi
[ -f knowledge/design-system.md ] && echo "design-system.md: OK" || echo "design-system.md: MISSING"
MINIMG=$(grep -o 'min_images=[0-9]*' knowledge/design-system.md 2>/dev/null | head -1 | cut -d= -f2)
echo "min_images: ${MINIMG:-5}"
echo "photos: $(find photos -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) 2>/dev/null | wc -l | tr -d ' ')"
for s in fetch_posts.py fetch_post.py dedupe_check.py lint_post.py gen_image.py naver_upload.sh; do
  if [ ! -f "scripts/$s" ]; then echo "script: MISSING $s"
  elif ! cmp -s "scripts/$s" "${CLAUDE_PLUGIN_ROOT}/scaffold/scripts/$s"; then echo "script: OUTDATED $s"; fi
done
BLOG_ID=pajuclark
[ -f knowledge/source-blogs.json ] && \
  BLOG_ID=$(python3 -c "import json;o=json.load(open('knowledge/source-blogs.json')).get('own_blog');print((o.get('blogId') if isinstance(o,dict) else o) or 'pajuclark')" 2>/dev/null || echo pajuclark)
echo "blogId: $BLOG_ID"
if command -v naver-blog-cli >/dev/null 2>&1; then
  SESS=$(NAVER_BLOG_ID="$BLOG_ID" naver-blog-cli check-session 2>&1)
  if echo "$SESS" | grep -q '세션 정상' && echo "$SESS" | grep -q '글쓰기 가능'; then echo "session: OK"
  else echo "session: LOGIN_NEEDED — $(echo "$SESS" | head -1)"; fi
else echo "session: MISSING (naver-blog-cli 없음)"; fi
for f in "${CLAUDE_PLUGIN_ROOT}/skills/blog-draft-writer/SKILL.md" \
         "${CLAUDE_PLUGIN_ROOT}/skills/blog-draft-writer/references/structure-templates.md" \
         "${CLAUDE_PLUGIN_ROOT}/skills/blog-naver-seo/SKILL.md" \
         "${CLAUDE_PLUGIN_ROOT}/skills/blog-fact-check/SKILL.md" \
         "${CLAUDE_PLUGIN_ROOT}/skills/blog-fact-check/references/claim-types.md"; do
  [ -f "$f" ] && echo "skill: OK $f" || echo "skill: MISSING $f"
done
```

| 결과 | 조치 |
|---|---|
| `work-folder: MISSING` | "작업 폴더가 아닙니다. 먼저 `/clark-blog:blog-setup`을 실행하세요." 안내 후 **중단** |
| `GEMINI_API_KEY: MISSING` | `/clark-blog:blog-setup`의 GEMINI 안내(https://aistudio.google.com/apikey → 작업 폴더 `.env`에 `GEMINI_API_KEY=…`, 채팅에 붙여넣지 않기)를 **경고로 보여 주고 계속**. 이 실행은 "키 없음 모드": Step 3에서 photo 슬롯만 처리하고 ai 슬롯은 `보류`. 이때 `photos:` < `min_images:`이면 실사진만으로 이미지 수를 못 채워 업로드까지 갈 수 없다 — B 발주 전에 묻는다(아래 [B] 참고) |
| `design-system.md: MISSING` | "`blog-design-system` 스킬로 디자인 시스템을 먼저 만들어 주세요." 안내 후 **중단** |
| `session: LOGIN_NEEDED` / `MISSING` | "업로드 전까지 로그인해 두세요"라고 **경고하고 계속**(Step 4까지 진행). 이 실행은 "세션 없음 모드": Step 5는 `--dry-run`만 하고 로그인 안내 후 끝낸다 |
| `skill: MISSING` | 플러그인 설치가 깨짐 — 경로를 보고하고 **중단** |
| `script: MISSING` / `script: OUTDATED` | 작업 폴더 `scripts/`가 없거나 플러그인보다 오래됨 → "`/clark-blog:blog-setup <작업 폴더>`를 다시 실행하세요(scripts는 최신본으로 갱신, knowledge는 보존)." 재실행 안내 후 **중단** |

중단할 항목이 없으면(경고 항목은 모드만 기억하고) 기발행 글 목록을 갱신한다(`<blogId>`는 위 출력값):

```bash
python3 scripts/fetch_posts.py --all <blogId> --out work/pajuclark-posts.json
```

실패하면 중단·보고. 위 `skill: OK` 줄의 절차 스킬 5개 **절대경로**를 기억해 둔다 — 아래 발주·재개 메시지의 `${CLAUDE_PLUGIN_ROOT}/…` 자리에는 이 절대경로를 넣는다(변수 문자열 그대로 넘기지 않는다).

## Step 1. 주제 리서치 (메인)

- 인자로 번호가 왔고 `work/topics/$(date +%F)-topics.md`가 있으면 → 리서치를 건너뛰고 게이트 1로.
- 그 밖에는 **Skill 도구로** `clark-blog:blog-topic-research`를 실행해 메인이 직접 수행한다(서브에이전트 아님). Step 0에서 `work/pajuclark-posts.json`을 방금 갱신했으므로 스킬의 1단계(`--all` 갱신)는 건너뛰어도 된다. 스킬의 자체검증이 `ALL OK`여야 끝난다.
- 산출: `work/topics/<YYYY-MM-DD>-topics.md`(열 10개: 번호 | 제목안 | 핵심 키워드 | 검색 의도 | 출처 글(링크) | 출처 글 chars/images | 우리 블로그 중복 | 추천 유형 | 추가 리서치 포인트 | 변주 제안).

## ● 게이트 1 — 주제 선택

topics 표를 이랑에게 그대로 보여 준 뒤 **AskUserQuestion** 한 번으로 묻는다.

1. 번호 — 옵션은 추천 후보 최대 4개(`<번호>. <제목안>`), 그 밖의 번호는 기타 입력. 인자로 번호가 왔으면 그 번호를 첫 옵션으로.
2. 유형 — `정보` / `홍보`(해당 행의 "추천 유형"을 첫 옵션으로).
3. 지역 키워드 2개 — multiSelect: `의정부` / `양주` / `동두천` / `포천`(`서울북부`는 기타 입력). 정확히 2개가 아니면 이 질문만 다시 묻는다.

번호를 여러 개 고르면 이번 실행은 **한 편만** 진행한다 — 어느 번호부터 할지 한 번 더 묻고, 나머지는 종료 보고에 "`/clark-blog:blog-run <번호>`로 이어서" 안내한다(하루 1~2편 이내).

선택이 끝나면 글 폴더를 만든다.

```bash
LAST=$(ls -d work/posts/[0-9][0-9][0-9]-* 2>/dev/null | sed -E 's#.*/([0-9]{3})-.*#\1#' | sort -n | tail -1)
NNN=$(printf '%03d' $((10#${LAST:-0} + 1))); echo "NNN=$NNN"
```

- slug = 고른 행의 제목안 핵심어 2~4개를 `-`로 이은 것(한글 그대로, 공백·기호 제거, 40자 이내). 예: `001-지게차운전기능사-실기-준비`.
- `mkdir -p work/posts/<NNN-slug>/images`
- `P/topic.md` = topics 파일의 표 머리 줄 + 구분선 + 고른 행 **원문 그대로**(3줄).
- `P/gates.md`를 만들고 `## 선택`을 쓴다:

```markdown
# gates — <NNN-slug>

## 선택
- 일시: 2026-10-07 10:30
- 번호: 3
- 유형: 정보
- 지역 키워드: 의정부, 양주
- 카테고리: 클라크중장비운전학원
- topics 파일: work/topics/2026-10-07-topics.md
- topics 행: | 3 | … (고른 행 원문 그대로) … |
```

카테고리는 이랑이 다른 것을 지정할 때만 바꾼다(`knowledge/source-blogs.json`의 `own_blog.categories` 값 중 하나).

## [B] 초안 — `clark-blog:blog-writer` 발주 (디스패치 1)

**발주 전 확인(키 없음 + 실사진 부족)**: 키 없음 모드이고 Step 0의 `photos:` 값이 `min_images:`보다 작으면, 이 글은 이미지 수 기준을 채우지 못해 임시저장까지 갈 수 없다. 이유를 한 줄로 알리고 **AskUserQuestion** `초안까지만 진행(업로드 불가)` / `중단하고 키·사진 준비`.
- `중단하고 키·사진 준비` → `.env`의 `GEMINI_API_KEY`(blog-setup GEMINI 안내, 결제 설정된 프로젝트의 키) 또는 `photos/`에 실사진 `min_images`장 이상을 준비하라고 안내하고 끝낸다(디스패치 0).
- `초안까지만 진행(업로드 불가)` → 그대로 B부터 진행한다. Step 3 끝의 "확정 이미지 수 확인"에서 멈추고 `resume`을 안내하게 된다.

```
Agent 도구
  subagent_type: clark-blog:blog-writer
  name: blog-writer-<NNN>
  prompt:
    mode: B
    글 폴더: work/posts/<NNN-slug>/
    입력: work/posts/<NNN-slug>/gates.md (## 선택), work/posts/<NNN-slug>/topic.md,
          knowledge/design-system.md, knowledge/academy-profile.md, knowledge/law-sources.md,
          work/variation-log.md (없을 수 있음), work/pajuclark-posts.json
    절차 스킬: ${CLAUDE_PLUGIN_ROOT}/skills/blog-draft-writer/SKILL.md
              ${CLAUDE_PLUGIN_ROOT}/skills/blog-draft-writer/references/structure-templates.md
    출력: work/posts/<NNN-slug>/research.md, work/posts/<NNN-slug>/draft.md
```

반환을 받으면 `ls P/research.md P/draft.md`로 확인하고, 반환의 lint 결과·`[출처 필요]` 건수·`## 질문`을 기록해 둔다. `## 질문`(예: ⑨ 홍보 비율 초과)은 아래 "질문 처리"대로 이랑에게 묻는다.

## [C] 근거 검토 — `clark-blog:blog-fact-checker` 발주 (디스패치 2)

```
Agent 도구
  subagent_type: clark-blog:blog-fact-checker
  name: blog-fact-checker-<NNN>-r1
  prompt:
    회차: r1
    초안: work/posts/<NNN-slug>/draft.md
    리서치: work/posts/<NNN-slug>/research.md
    지식: knowledge/law-sources.md, knowledge/academy-profile.md
    절차 스킬: ${CLAUDE_PLUGIN_ROOT}/skills/blog-fact-check/SKILL.md
              ${CLAUDE_PLUGIN_ROOT}/skills/blog-fact-check/references/claim-types.md
    출력: work/posts/<NNN-slug>/factcheck.md
```

반환 뒤 요약 줄과 질문 여부를 읽는다:

```bash
F=work/posts/<NNN-slug>/factcheck.md
S=$(grep -m1 -E '^요약: PASS [0-9]+ \| FAIL [0-9]+ \| 출처필요 [0-9]+ \| 시점확인 [0-9]+' "$F") || { echo "요약 줄 없음"; exit 1; }
FAIL=$(echo "$S" | sed -E 's/.*FAIL ([0-9]+).*/\1/'); NEED=$(echo "$S" | sed -E 's/.*출처필요 ([0-9]+).*/\1/')
echo "$S"; echo "FAIL+출처필요=$((FAIL + NEED))"
grep -q '^## 질문' "$F" && echo "질문: 있음" || echo "질문: 없음"
```

"요약 줄 없음"이면 중단·보고(완료되지 않은 리포트).

### 질문 처리 (C·B·B' 공통)

`factcheck.md`(또는 `factcheck-r2.md`)에 `## 질문`이 있으면 **FAIL+출처필요 건수와 무관하게** 다음 디스패치 전에 이랑에게 묻는다. writer 반환의 `## 질문`, `seo.md` 끝 "메인에 전달"도 같다.
- AskUserQuestion으로 질문을 원문 그대로(id 포함) 묻는다(한 번에 최대 4개, 넘으면 나눠서).
- 답은 즉시 `P/gates.md`에 `## 초안피드백` 절로 append한다: `- 일시: …` · `- 질문 답: <id> — <이랑 답 원문>`(여러 줄). 이전 `## 초안피드백`이 있으면 그 절의 `제목:`·`톤:`·`길이:`·`수정 요청 원문:`·기존 `질문 답:` 줄을 새 절에 그대로 옮겨 적는다(마지막 절만 유효하므로 앞 내용이 사라지지 않게). 게이트 2 기록 때 다시 쓰는 `## 초안피드백`에도 `질문 답:` 줄을 그대로 옮겨 적는다.
- 다음 writer 재개 메시지에 `질문 답:` 원문을 넣는다.

## [B'] 수정 + SEO — writer 재개 (디스패치 3)

`SendMessage`로 `blog-writer-<NNN>`을 재개한다. FAIL+출처필요 수에 따라 범위가 다르다.

**(a) FAIL+출처필요 ≥ 1 — 전체 B'**

```
SendMessage → blog-writer-<NNN>
  mode: B'
  범위: 전체(팩트체크 반영 + SEO + 관련글 실제 URL 치환 + frontmatter)
  factcheck: work/posts/<NNN-slug>/factcheck.md
  SEO 스킬: ${CLAUDE_PLUGIN_ROOT}/skills/blog-naver-seo/SKILL.md
  추가 입력: knowledge/naver-seo-checklist.md, work/pajuclark-posts.json
  질문 답: <있으면 이랑 답 원문, 없으면 생략>
  출력: work/posts/<NNN-slug>/draft-v2.md, work/posts/<NNN-slug>/seo.md
```

**(b) FAIL+출처필요 = 0 — B' 생략 규칙**: 메인이 먼저 복사한 뒤 범위를 좁혀 재개한다.

```bash
cp work/posts/<NNN-slug>/draft.md work/posts/<NNN-slug>/draft-v2.md
```

```
SendMessage → blog-writer-<NNN>
  mode: B'
  범위: SEO·링크 치환·frontmatter만 (FAIL+출처필요 0건 — draft-v2.md는 메인이 draft.md에서 복사해 둠.
        팩트 반영은 건너뛰고 factcheck.md의 ## 시점 표기 권고만 반영)
  factcheck: work/posts/<NNN-slug>/factcheck.md
  SEO 스킬: ${CLAUDE_PLUGIN_ROOT}/skills/blog-naver-seo/SKILL.md
  추가 입력: knowledge/naver-seo-checklist.md, work/pajuclark-posts.json
  질문 답: <있으면>
  출력: work/posts/<NNN-slug>/draft-v2.md, work/posts/<NNN-slug>/seo.md
```

반환 뒤 `ls P/draft-v2.md P/seo.md`. 반환의 **"사실 문장 변경"** 줄을 기억한다(`없음`이 아니면 미검증 사실 변경 — 게이트 2에서 보여 주고 수정 루프의 C r2로 검토). `## 질문`·`seo.md` "메인에 전달"은 질문 처리대로.

## Step 2. lint (메인)

```bash
python3 scripts/lint_post.py work/posts/<NNN-slug>/draft-v2.md --stage draft --json > work/posts/<NNN-slug>/lint.json; echo "exit=$?"
```

- exit 0 → 게이트 2로.
- exit 1(FAIL) → B' 재개 **1회**(디스패치 +1):
  ```
  SendMessage → blog-writer-<NNN>
    mode: B'
    범위: lint FAIL 항목만
    lint: work/posts/<NNN-slug>/lint.json
    출력: work/posts/<NNN-slug>/draft-v2.md
  ```
  재개 뒤 같은 lint를 다시 돌려도 FAIL이면 멈추고 FAIL id·값을 보고한다.
- exit 2 → 사용 오류. 중단·보고.

lint.json 형식: `{"stage", "pass", "checks": [{"id","value","rule","result","detail"}], "stats"}`. draft 단계에서 보는 id: `forbidden`·`chars`·`h2_count`·`images`·`sources`·`placeholder_sources`·`variation`.

## ● 게이트 2 — 초안 피드백

이랑에게 보여 준다: `P/draft-v2.md` 본문 전체, 제목 A안(frontmatter `title`)·B안(`<!-- 제목 B안: … -->`), factcheck 요약 줄과 `## 시점 표기 권고`, lint.json의 `pass`·chars·h2_count·images·sources, `seo.md`의 표(요약), writer가 보고한 "사실 문장 변경".

**AskUserQuestion**:
1. 제목 — `A안: <제목>` / `B안: <제목>`(기타 입력으로 직접 쓴 제목도 받는다. 핵심 키워드가 그대로 들어 있어야 한다고 함께 안내).
2. 톤·길이·내용 — `그대로 진행` / `더 짧고 간결하게` / `더 친근한 말투로`(구체적 수정 요청은 기타 입력 원문 그대로 받는다).

`P/gates.md`에 append:

```markdown
## 초안피드백
- 일시: …
- 제목: A안 | B안 | 직접 — <채택 제목 원문>
- 톤: <답 원문 또는 "그대로">
- 길이: <답 원문 또는 "그대로">
- 수정 요청 원문: <기타 입력 원문, 없으면 "없음">
- 질문 답: <앞서 받은 답이 있으면 그대로 옮김>
```

- **A안 + 그대로 진행**이고 미검증 사실 변경이 없으면 → 디스패치 없이 Step 3.
- 그 밖(B안·직접 제목·수정 요청, 또는 앞선 B'의 사실 문장 변경이 `없음`이 아님) → **수정 루프 1회**:
  1. 제목·톤·길이·수정 요청 중 바꿀 것이 있을 때만 B' 재개(디스패치 +1):
     ```
     SendMessage → blog-writer-<NNN>
       mode: B'
       범위: 게이트 2 피드백 — work/posts/<NNN-slug>/gates.md 의 마지막 ## 초안피드백
       출력: work/posts/<NNN-slug>/draft-v2.md, work/posts/<NNN-slug>/seo.md
     ```
  2. 이번 글의 B' 반환(앞선 B'·lint 재개·1의 재개) 중 하나라도 "사실 문장 변경"이 `없음`이 아니면 C r2 발주(디스패치 +1, 새 Agent):
     ```
     Agent 도구
       subagent_type: clark-blog:blog-fact-checker
       name: blog-fact-checker-<NNN>-r2
       prompt:
         회차: r2
         초안: work/posts/<NNN-slug>/draft-v2.md
         리서치: work/posts/<NNN-slug>/research.md
         지식: knowledge/law-sources.md, knowledge/academy-profile.md
         절차 스킬: ${CLAUDE_PLUGIN_ROOT}/skills/blog-fact-check/SKILL.md
                   ${CLAUDE_PLUGIN_ROOT}/skills/blog-fact-check/references/claim-types.md
         출력: work/posts/<NNN-slug>/factcheck-r2.md
     ```
     C와 같은 명령으로 `factcheck-r2.md` 요약 줄을 읽는다. 질문이 있으면 질문 처리. FAIL+출처필요 ≥ 1 또는 `## 시점 표기 권고`가 `없음`이 아니면 B' 재개(디스패치 +1): `mode: B'` · `범위: 팩트체크 r2 반영` · `factcheck: work/posts/<NNN-slug>/factcheck-r2.md` · `질문 답:`(있으면). 0건·권고 없음이면 재개하지 않는다.
  3. Step 2 lint를 다시 돌린다(FAIL이면 Step 2 규칙대로 B' 재개 1회).
  4. 바뀐 부분(제목·수정 요청 반영 결과·r2 요약)을 보여 주고 AskUserQuestion `이미지 단계로 진행` / `여기서 중단`. 이 루프는 **한 번만** 돈다 — 추가 수정 요청이면 멈추고 보고한다(이랑이 직접 고치거나 다음 실행에서 이어 감).
- 위 어느 디스패치든 8회째가 되면 하지 않고 멈춘다(예산, 최대 7회).

## Step 3. 이미지 (메인)

**Skill 도구로** `clark-blog:blog-image-director`를 실행해 메인이 직접 수행한다(입력 `work/posts/<NNN-slug>/draft-v2.md`·`gates.md`). 산출: `P/images/image-plan.md`(열: 슬롯 | 위치(소제목) | 목적 | 유형 | 프롬프트(ai) / 후보 파일(photo) | 캡션(alt) | 파일 | 검수), `P/images/NN-<slug>.png`(ai 슬롯), 게이트 3용 요약.

- **키 없음 모드**(Step 0 `GEMINI_API_KEY: MISSING`) 또는 요약에 **"Gate: GEMINI 키 대기"**가 있으면: 생성은 하지 않는다(스킬 1~5단계로 image-plan.md를 쓰고 photo 후보만 고른다). image-plan.md에서 `유형`이 `ai`인 행의 `파일`을 `보류`, `검수`를 `키 없음`으로 적는다. 이랑이 그 자리에서 키를 채웠다고 하면 `uv run --with google-genai --with pillow scripts/gen_image.py work/posts/<NNN-slug>/images/image-plan.md`를 실행해 보류를 풀어도 된다. 그 뒤 생성된 각 이미지를 Read로 열어 blog-image-director 스킬 7단계 기준(글자·얼굴·중복·캡션·로고)으로 검수하고 image-plan.md `검수` 열을 갱신한 다음 게이트 3으로 간다. 이 생성도 스킬의 한도(ai 슬롯 수 × 3)에 포함한다.
- `파일` 경로 규칙: ai = **글 폴더 기준** `images/NN-<slug>.png`, photo = **작업 폴더 기준** `photos/<파일>`.

## ● 게이트 3 — 이미지 승인 (슬롯별)

슬롯마다 위치·유형·캡션·파일(ai는 절대경로를 보여 줘 이랑이 열어 볼 수 있게, photo는 후보 목록)·검수 결과를 보여 준다.
**AskUserQuestion**으로 슬롯별로 묻는다(한 호출에 최대 4슬롯, 넘으면 나눠서):
- ai 슬롯: `승인` / `재생성`(바꿀 점은 기타 입력) / `실사진으로 교체`(파일명은 기타 입력) / `제거`
- photo 슬롯: 후보 파일 최대 3개(`photos/…`) / `제거`(다른 파일·AI 전환은 기타 입력)
- `보류` 슬롯(키 없음): `보류 유지`(final.md에서 빠지고 나중에 Step 3 재실행) / `제거` / `실사진으로 교체`(파일명은 기타 입력)

`P/gates.md`에 append:

```markdown
## 이미지승인
- 일시: …
- 01: 승인 — images/01-cover.png
- 02: 후보 선택 — photos/교육장-01.jpg
- 03: 재생성 — 요청: <원문>
- 04: 제거
```

반영(메인이 직접, **디스패치 아님**):
- 후보 선택·실사진 교체 → `image-plan.md` 그 행의 `유형`을 `photo`, `파일`을 `photos/<파일>`, `검수`를 `이랑 지정`으로 고친다(파일이 실제로 있는지 `ls`).
- 재생성 → 요청대로 그 행의 프롬프트를 고친 뒤
  ```bash
  uv run --with google-genai --with pillow scripts/gen_image.py work/posts/<NNN-slug>/images/image-plan.md --only NN
  ```
  새 이미지를 Read로 열어 검수하고(스킬 7단계 기준) `검수` 열을 갱신한 뒤 그 슬롯만 다시 묻는다. 슬롯당 재생성 최대 2회, 글 전체 생성 호출 ai 슬롯 수 × 3 이내(스킬 규칙). 넘으면 `제거`·실사진 중에서 고르게 한다.
- 제거 → 그 행의 `파일`을 `제거`, `검수`를 `제거(이랑)`로 고친다. 보류 유지 → 그대로 둔다(`파일` = `보류`).

모든 슬롯이 승인·확정·제거·보류 유지로 끝나면 마지막 결과로 `## 이미지승인`을 한 번 더 append한다(재질문이 있었던 경우).

**확정 이미지 수 확인**(Step 4로 가기 전, 매번):

```bash
python3 - work/posts/<NNN-slug> <<'PY'
import re, sys
sys.path.insert(0, "scripts"); from gen_image import parse_plan
P = sys.argv[1].rstrip("/")
_, rows = parse_plan(open(f"{P}/images/image-plan.md", encoding="utf-8").read())
m = re.search(r"min_images=(\d+)", open("knowledge/design-system.md", encoding="utf-8").read())
need = int(m.group(1)) if m else 5
ok = sum(1 for r in rows if r["file"].strip("` ").startswith(("images/", "photos/")))   # 보류·제거 제외
print(f"확정 이미지: {ok} / 필요 {need}")
PY
```

- 확정 이미지 ≥ 필요 → Step 4.
- 확정 이미지 < 필요 → **Step 4로 가지 않고 멈춘다**(final.md를 만들지 않음). 이랑에게 "확정 이미지 n장 / 필요 m장 — 키 또는 실사진 준비 후 `/clark-blog:blog-run resume <NNN>`"이라고 알리고 종료 보고로 간다(키는 결제 설정된 프로젝트의 `GEMINI_API_KEY`, 실사진은 `photos/`에). image-plan.md·gates.md는 그대로 두어 `resume`이 이어받게 한다.

## Step 4. `final.md` 생성 (메인)

`draft-v2.md`의 `![슬롯: …]()`을 등장 순서(01, 02, …)대로 `image-plan.md`의 같은 슬롯 행과 맞춰 `![<캡션(alt)>](<절대경로>)`로 바꾼다. `파일`이 `images/…`면 글 폴더 기준, `photos/…`면 작업 폴더 기준으로 절대경로를 만들고, `제거`·`보류`면 그 줄을 지운다(지운 자리의 연속 빈 줄은 하나로 줄인다). frontmatter·B안 주석·본문 나머지는 그대로 둔다(B안 주석은 업로드 스크립트가 지운다).

```bash
python3 - work/posts/<NNN-slug> <<'PY'
import os, re, sys
sys.path.insert(0, "scripts"); from gen_image import parse_plan   # image-plan.md 표 파서(표준 라이브러리만)
P = sys.argv[1].rstrip("/")
_, rows = parse_plan(open(f"{P}/images/image-plan.md", encoding="utf-8").read())
plan = {r["slot"]: r for r in rows}
out, n, err = [], 0, []
for line in open(f"{P}/draft-v2.md", encoding="utf-8").read().splitlines():
    if not re.fullmatch(r"\s*!\[슬롯:[^\]]*\]\(\s*\)\s*", line):
        out.append(line); continue
    n += 1; k = "%02d" % n; r = plan.get(k)
    f = (r or {}).get("file", "").strip("` ")
    if r is None:
        err.append(f"{k}: image-plan.md에 행 없음")
    elif f in ("제거", "보류"):
        continue                                   # 제거·보류 슬롯은 줄째 삭제
    elif f.startswith("images/"):
        a = os.path.abspath(os.path.join(P, f))    # ai = 글 폴더 기준
    elif f.startswith("photos/"):
        a = os.path.abspath(f)                     # photo = 작업 폴더 기준
    else:
        err.append(f"{k}: 파일 칸 미확정({f or '빈칸'})")
    if r is None or not (f.startswith("images/") or f.startswith("photos/")):
        out.append(line); continue
    if not os.path.isfile(a):
        err.append(f"{k}: 파일 없음 {a}")
    out.append(f"![{r['caption']}]({a})")
if n != len(rows):
    err.append(f"슬롯 수 불일치: draft-v2.md {n}개 / image-plan.md {len(rows)}행")
if err:
    sys.exit("final.md를 만들지 않았습니다:\n" + "\n".join(err))
text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).rstrip("\n") + "\n"   # 지운 줄 자리의 연속 빈 줄 정리
open(f"{P}/final.md", "w", encoding="utf-8").write(text)
cnt = lambda v: sum(1 for r in rows if r["file"].strip("` ") == v)
print(f"final.md 작성 — 슬롯 {n}개(제거 {cnt('제거')}개, 보류 {cnt('보류')}개)")
PY
python3 scripts/lint_post.py work/posts/<NNN-slug>/final.md --stage final --json > work/posts/<NNN-slug>/lint.json; echo "exit=$?"
```

- 스크립트가 "final.md를 만들지 않았습니다"로 끝나면 그 사유대로 Step 3(게이트 3)으로 돌아가 슬롯을 확정한다.
- **Step 4 → Step 3 되돌아가기는 글 1편당 1회**(아래 lint FAIL의 이미지 쪽 포함). 두 번째로 필요해지면 멈추고 보고한다.
- lint exit 0 → Step 5. exit 2 → 중단·보고.
- lint exit 1 → FAIL id별로 처리한다(lint.json의 `checks[].result == "FAIL"`):
  - 이미지 쪽 `image_paths`·`images`(제거로 장수 부족 등) → Step 3/게이트 3에서 해당 슬롯을 다시 정한 뒤 Step 4 재실행.
  - 캡션 쪽 `seo_image_captions` → 메인이 `image-plan.md`의 `캡션(alt)`을 고친 뒤 Step 4 재실행.
  - 텍스트 쪽(`forbidden`·`chars`·`h2_count`·`sources`·`placeholder_sources`·`related_links`·`title_keyword`·`tags_count`·`frontmatter`·`variation`·`h1_once`·`seo_title_length`·`seo_keyword_body`·`seo_keyword_h2`) → B' 재개 1회(디스패치 +1, `범위: lint FAIL 항목만` · `lint: work/posts/<NNN-slug>/lint.json` · "final.md가 아니라 draft-v2.md를 고칠 것") → Step 4 재실행. 그래도 FAIL이면 멈추고 보고.

## Step 5. 업로드 (메인 — 서브에이전트 금지: 로그인·2단계 인증·CAPTCHA 개입 가능)

**Skill 도구로** `clark-blog:blog-naver-upload`를 실행해 그 절차대로 메인이 직접 수행한다. 출력은 stdout·stderr를 함께 받는다(경고 줄이 stderr에도 나온다).

`<blogId>`는 Step 0 출력의 `blogId:` 값(`own_blog.blogId`) — 세션 확인과 업로드가 같은 블로그를 쓰게 항상 넘긴다.

1. dry-run — lint·frontmatter·이미지 경로만 확인(세션 확인·업로드 생략). title·category·tags·이미지 수를 이랑에게 보여 준다.
   ```bash
   bash scripts/naver_upload.sh work/posts/<NNN-slug>/final.md --blog-id <blogId> --dry-run 2>&1; echo "exit=$?"
   ```
   **세션 없음 모드**(Step 0 `session: LOGIN_NEEDED`/`MISSING`)면 여기서 멈춘다: dry-run 결과를 보여 주고 `/clark-blog:blog-setup` 4단계 로그인 절차(작업 폴더에서 `login_setup.py`, "로그인 상태 유지" 체크, 사람이 직접)를 안내한 뒤 "로그인 후 `/clark-blog:blog-run resume <NNN>`으로 업로드만 이어서"라고 알리고 종료 보고로 간다. `## 업로드`와 variation-log 줄은 **쓰지 않는다**.
2. dry-run이 exit 0일 때만 실제 임시저장(따로 호출). 창이 뜨고 수 분 걸릴 수 있다고 미리 알린다.
   ```bash
   bash scripts/naver_upload.sh work/posts/<NNN-slug>/final.md --blog-id <blogId> 2>&1; echo "exit=$?"
   ```

종료 코드별 대응(dry-run도 같은 코드를 쓴다):

| exit | 의미 | 대응 |
|---|---|---|
| 0 | 임시저장 완료 | 아래 "성공 기록" |
| 2 | 사용 오류(경로·frontmatter) | 인자와 `final.md` frontmatter 확인 후 중단·보고 |
| 10 | `lint_post.py` 실패 | Step 4의 FAIL id별 처리와 같음(텍스트 → B' 재개, 이미지 → Step 3/4) |
| 11 | 이중 검사 실패(금칙어·`[[`·빈 이미지·`[출처 필요]`) | lint 규칙 구멍이다 — 출력된 줄을 원인에 맞게 고친 뒤(텍스트는 B' 재개) 이랑에게 한 줄 보고 |
| 12 | 이미지 경로가 절대경로가 아니거나 파일 없음 | Step 4 재실행(image-plan.md 기준 절대경로 치환) |
| 20 | 세션 없음/만료 또는 `naver-blog-cli` 없음 | `/clark-blog:blog-setup` 4단계 로그인 절차 안내("로그인 상태 유지" 체크, 사람이 직접) → 끝났다고 하면 같은 명령 1회 재실행 |
| 30 | `create-draft` 실패 | 출력된 CLI 문구를 이랑에게 보여 주고(에디터 변경·이미지 10MB·세션 만료), 네이버 임시저장 글에 중복이 생겼는지 확인을 요청한 뒤 재시도는 1회까지 |
| 31 | 저장됐으나 목록에서 제목 확인 불가 | 이랑에게 "네이버 → 글쓰기 → 임시저장 글"에서 직접 확인 요청. 있으면 성공으로 기록 |

같은 오류로 재시도는 한 번까지. 반복 실패하면 멈추고 보고한다(계정 안전). `publish-draft`·`delete-draft`는 호출하지 않는다.

**성공 기록**(메인):

1. `P/gates.md`에 append:
   ```markdown
   ## 업로드
   - 일시: …
   - 제목: <임시저장 제목>
   - 카테고리·태그: <스크립트 출력 그대로>
   - list-drafts 확인: <upload.log의 "성공 | … | list-drafts: …" 줄의 list-drafts 값, exit 31이면 "이랑 직접 확인">
   - 경고: <"경고: 카테고리/태그 설정 실패" 출력이 있었으면 그 줄, 없으면 "없음">
   - 로그: work/posts/<NNN-slug>/upload.log
   ```
2. `work/variation-log.md`에 한 줄 추가(`final.md` frontmatter `variation`에서 읽음, region은 `+`로 연결):
   ```bash
   python3 - work/posts/<NNN-slug> <<'PY'
   import os, re, sys, datetime
   sys.path.insert(0, "scripts"); import lint_post
   P = sys.argv[1].rstrip("/")
   fm, _, err = lint_post.parse_frontmatter(open(f"{P}/final.md", encoding="utf-8").read().splitlines())
   v = str((fm or {}).get("variation", ""))
   one = lambda k: (re.search(rf"\b{k}\s*:\s*([^,}}\[]+)", v) or [None, ""])[1].strip()
   reg = re.search(r"\bregion\s*:\s*\[([^\]]*)\]", v)
   region = "+".join(x.strip() for x in reg.group(1).split(",") if x.strip()) if reg else ""
   vals = [one("type"), one("structure"), one("intro"), region, one("cta")]
   if err or not all(vals):
       sys.exit(f"variation 읽기 실패: {v!r}")
   line = " | ".join([datetime.date.today().isoformat(), "posts/" + os.path.basename(P)] + vals)
   with open("work/variation-log.md", "a", encoding="utf-8") as f:
       f.write(line + "\n")
   print(line)
   PY
   ```
   형식: `YYYY-MM-DD | posts/NNN-slug | type | structure | intro | region | cta` (예: `2026-10-07 | posts/001-지게차운전기능사-실기-준비 | 정보 | 절차형 | 상황 | 의정부+양주 | 관련글`).

## ● 종료 보고

이랑에게 보고한다:
- 임시저장 제목 · 카테고리 · 태그 · 이미지 수(스크립트 출력값)
- 스크립트 출력에 `경고: 카테고리/태그 설정 실패`가 있었으면 반드시: "임시저장은 됐지만 카테고리·태그가 빠졌을 수 있습니다. 임시저장 글에서 직접 확인해 주세요."
- 안내 문구: **"네이버 앱/웹 → 글쓰기 → 임시저장 글 → 미리보기 → 발행"** (발행은 이랑이 직접)
- 보류 슬롯이 있으면(키 없음 모드): "AI 이미지 보류 n개 — 키 설정 후 `/clark-blog:blog-run resume <NNN>`". 그리고 **이번 final.md(임시저장본)는 계획보다 이미지가 n장 적다**는 것, `.env`에 키를 넣은 뒤 `resume <NNN>`을 실행하면 Step 3(이미지)부터 보류 슬롯을 채운 final.md를 새로 만들 수 있다는 것을 함께 알린다.
- 확정 이미지 부족으로 Step 3 뒤에서 멈췄으면: "final.md·임시저장은 아직 없습니다. 확정 이미지 n장 / 필요 m장 — 키 또는 실사진 준비 후 `/clark-blog:blog-run resume <NNN>`" (위 임시저장 항목·발행 안내 대신)
- 세션 없음 모드로 업로드를 미뤘으면: "임시저장은 아직 안 됐습니다. 로그인 후 `/clark-blog:blog-run resume <NNN>`" (위 임시저장 항목·발행 안내 대신)
- 글 폴더 경로, 디스패치 `n/7`, 게이트 1에서 남긴 번호가 있으면 "`/clark-blog:blog-run <번호>`로 이어서"

---

## resume NNN (멈춘 곳부터 이어서)

인자가 `resume NNN`이면 이 절만 수행한다. **디스패치는 하지 않는다.** 글 폴더 `P=$(ls -d work/posts/NNN-* | head -1)`에서 이어 갈 지점을 정한다.

- `P/final.md`가 있으면 → **업로드 재개**. 단 `P/images/image-plan.md`에 `파일`이 `보류`인 행이 있고 이번 preflight에서 `GEMINI_API_KEY`가 있으면, AskUserQuestion `보류 이미지 채우고 final.md 다시 만들기` / `지금 final.md로 업로드만` — 앞의 것이면 **이미지 재개**로 간다.
- `final.md`가 없고 `P/draft-v2.md`와 `P/gates.md`의 `## 초안피드백`이 있으면 → **이미지 재개**(Step 3부터).
- 둘 다 아니면 "이어서 할 단계가 없습니다 — `/clark-blog:blog-run`으로 게이트 2까지 먼저 진행하세요"라고 답하고 끝.

### 이미지 재개 (Step 3 → 게이트 3 → Step 4 → Step 5)

1. Step 0의 preflight Bash를 그대로 실행하고 Step 0 표대로 판정한다: `work-folder`·`script`·`skill`·`design-system.md`가 MISSING/OUTDATED이면 그 표의 안내 후 끝낸다. `GEMINI_API_KEY: MISSING`이면 키 없음 모드, `session`이 OK가 아니면 세션 없음 모드로 계속한다. `blogId`·`photos:`·`min_images:`를 기억한다.
2. Step 3을 수행한다. `P/images/image-plan.md`가 이미 있으면 새로 쓰지 않고 그 계획을 이어 쓴다: 키가 있으면 `파일`이 `보류`인 ai 슬롯만 `uv run --with google-genai --with pillow scripts/gen_image.py work/posts/<NNN-slug>/images/image-plan.md --only <보류 슬롯 번호(쉼표)>`로 생성하고 Step 3의 검수(스킬 7단계 기준·한도)를 따른다. 실사진을 준비했으면 게이트 3에서 그 슬롯을 `실사진으로 교체`로 고르게 한다.
3. 게이트 3 → 확정 이미지 수 확인(여전히 부족하면 다시 멈추고 같은 `resume` 안내) → Step 4 → Step 5 → 종료 보고. Step 4·5에서 B' 재개가 필요해지면(lint 텍스트 FAIL, exit 10·11) 디스패치하지 않고 실패 항목을 보고한 뒤 "`/clark-blog:blog-run`(전체 워크플로우)으로 고친 뒤 다시 `resume`"이라고 안내하고 끝낸다.

### 업로드 재개 (Step 5만 — 세션이 없어 업로드를 미뤘을 때)

1. Step 0의 preflight Bash를 그대로 실행하고 Step 0 표대로 판정한다: `work-folder: MISSING`·`script: MISSING`/`OUTDATED`·`skill: MISSING`이면 그 표의 안내 후 끝낸다. `blogId`를 기억한다. `session: OK`가 아니면 로그인 안내 후 끝낸다(`GEMINI_API_KEY`·`design-system.md`는 업로드와 무관 — 무시. 단 위의 보류 이미지 질문에는 `GEMINI_API_KEY` 결과를 쓴다).
2. `gates.md`에 `## 업로드`가 이미 있으면 "이미 임시저장했습니다(<일시>)"라고 알리고, 다시 올릴지 AskUserQuestion `다시 올리기` / `그만두기`(중복 임시저장 주의).
3. `python3 scripts/lint_post.py <P>/final.md --stage final --json > <P>/lint.json` — exit 1이면 FAIL id를 보고하고 끝낸다(텍스트 수정이 필요하면 이 명령이 아니라 전체 워크플로우로).
4. Step 5의 dry-run → 실제 임시저장(`--blog-id <blogId>`) → exit code 표대로 대응 → 성공 기록(`## 업로드` + variation-log 1줄) → 종료 보고.
   단 `resume`에서는 **디스패치하지 않는다**: exit 10(lint 실패)·11(이중 검사 실패)이 나오면 B' 재개(디스패치)가 필요하므로 출력된 실패 항목을 보고하고 "`/clark-blog:blog-run`(전체 워크플로우)으로 고친 뒤 다시 `resume`"이라고 안내하고 끝낸다. exit 12도 Step 4가 필요하므로 같은 방식으로 안내하고 끝낸다.

---

## report NNN (상태 요약만)

인자가 `report NNN`이면 이 절만 수행한다. 파일을 쓰거나 고치지 않고, 디스패치·업로드·preflight를 하지 않는다.

```bash
P=$(ls -d work/posts/NNN-* 2>/dev/null | head -1); echo "P=${P:-없음}"
[ -n "$P" ] && ls -la "$P" "$P/images" 2>/dev/null
[ -n "$P" ] && grep -n '^## \|^- ' "$P/gates.md" 2>/dev/null
[ -n "$P" ] && [ -f "$P/lint.json" ] && python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('lint', d['stage'], 'pass=', d['pass']);[print(' FAIL', c['id'], c['value'], c['detail']) for c in d['checks'] if c['result']=='FAIL']" "$P/lint.json"
[ -n "$P" ] && grep -m1 '^요약:' "$P"/factcheck*.md 2>/dev/null
[ -n "$P" ] && tail -n 5 "$P/upload.log" 2>/dev/null
```

글 폴더가 없으면 "work/posts/NNN-* 글이 없습니다"라고만 답한다. 있으면 표로 요약한다: 단계(선택 · 초안(draft.md) · 팩트체크(요약 줄) · draft-v2 · 게이트 2 · 이미지(image-plan.md·승인) · final.md · lint(stage·pass·FAIL id) · 업로드(upload.log 마지막 결과)) | 상태 | 근거 파일. 마지막에 "다음 할 일" 한 줄.
