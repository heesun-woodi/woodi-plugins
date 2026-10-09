#!/usr/bin/env bash
# naver_upload.sh — final.md → 네이버 블로그 "임시저장"까지만 (발행은 사람).
# 사용: naver_upload.sh <posts/NNN-slug/final.md> [--blog-id pajuclark] [--category "이름"(frontmatter에 category가 없을 때의 대체값)] [--dry-run]
# 작업 폴더(cwd)에서 실행한다 (세션 파일 playwright-state/storage_state.json 이 cwd 기준).
# 동작: lint --stage upload → 이중 검사 → create-draft-from-folder (표지 images/00-cover.png 를 대표이미지로) → list-drafts 확인.
# 종료 코드: 0 성공 | 2 사용 오류 | 10 lint 실패 | 11 이중 검사 실패 | 12 이미지 문제(표지 없음·절대경로 아님·파일 없음)
#            20 세션 없음/만료 | 30 create-draft-from-folder 실패 | 31 list-drafts에서 제목 확인 불가
# naver-blog-cli 는 실패해도 exit 0 이므로 종료 코드가 아니라 stdout 문구로 판정한다.
set -u
export NAVER_BLOG_READONLY=1   # 발행·삭제 서브커맨드를 CLI에서 제거 — 임시저장까지만

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BLOG_ID="pajuclark"
CATEGORY_OPT=""
DRY=0
FINAL=""

while [ $# -gt 0 ]; do
  case "$1" in
    --blog-id) [ $# -ge 2 ] || { echo "오류: $1 값이 필요합니다." >&2; exit 2; }; BLOG_ID="$2"; shift 2 ;;
    --category) [ $# -ge 2 ] || { echo "오류: $1 값이 필요합니다." >&2; exit 2; }; CATEGORY_OPT="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    -*) echo "오류: 알 수 없는 옵션: $1" >&2; exit 2 ;;
    *) FINAL="$1"; shift ;;
  esac
done
if [ -z "$FINAL" ] || [ ! -f "$FINAL" ]; then
  echo "오류: final.md 경로가 없거나 파일이 없습니다. 사용: naver_upload.sh posts/NNN-slug/final.md [--blog-id ID] [--category 이름] [--dry-run]" >&2
  exit 2
fi
if [ -z "$BLOG_ID" ]; then echo "오류: --blog-id 값이 비었습니다." >&2; exit 2; fi

POSTDIR="$(cd "$(dirname "$FINAL")" && pwd)"
LOG="$POSTDIR/upload.log"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/naver-upload.XXXXXX")" || { echo "오류: 임시 폴더를 만들 수 없습니다." >&2; exit 2; }
trap 'rm -rf "$WORK"' EXIT

log() { printf '%s | %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG"; }
die() { code="$1"; shift; echo "$*" >&2; log "exit $code | $(printf '%s' "$*" | head -n1)"; exit "$code"; }

# 프론트매터·본문 처리 헬퍼 (lint_post.py 의 parse_frontmatter 재사용)
PYH='
import os, re, sys, json
sys.path.insert(0, sys.argv[1])
import lint_post
final, mode, out = sys.argv[2], sys.argv[3], sys.argv[4]
text = open(final, encoding="utf-8").read()
lines = text.splitlines()
fm, start, err = lint_post.parse_frontmatter(lines)
if mode == "precheck":
    kdir = lint_post.find_knowledge(final)
    bad = []
    for w in lint_post.load_forbidden(kdir):
        if w in text: bad.append("금칙어: " + w)
    if "[[" in text: bad.append("자리표시 [[ 잔존")
    if re.search(r"!\[[^\]]*\]\(\s*\)", text): bad.append("빈 이미지 경로 ![..]()")
    if re.search(r"\[출처 필요\]|\(출처 필요\)", text): bad.append("[출처 필요] 잔존")
    if re.search(r"\[출처\]\(", text): bad.append("[출처]( 링크형 출처 잔존 — scripts/build_final.py 재실행")
    if re.search(r"출처\s*:", text): bad.append("출처: 잔존 — scripts/build_final.py 재실행")
    if re.search(r"!\[[^\]]+\]\(", text): bad.append("alt(캡션) 있는 이미지 — scripts/build_final.py 재실행")
    if not re.search(r"^:::place\s+\S.*:::\s*$", text, re.M): bad.append(":::place 지시문 없음 — scripts/build_final.py 재실행")
    if not re.search(r"^\*\*#", text, re.M): bad.append("**# 해시태그 줄 없음 — scripts/build_final.py 재실행")
    print("\n".join(bad)); sys.exit(11 if bad else 0)
if err or fm is None:
    print("frontmatter 오류: " + str(err)); sys.exit(2)
body = lines[start:]
while body and not body[0].strip(): body.pop(0)
while body and re.match(r"^\s*<!--.*?-->\s*$", body[0]):   # 제목 B안/A안 주석
    body.pop(0)
    while body and not body[0].strip(): body.pop(0)
fence = False
for i, l in enumerate(body):          # 첫 ## 앞, 코드펜스 밖의 H1 한 줄 제거
    if re.match(r"^\s*(```|~~~)", l):
        fence = not fence
    elif not fence:
        if re.match(r"^##\s", l):
            break
        if re.match(r"^#\s+\S", l):
            del body[i]; break
btxt = "\n".join(body).strip() + "\n"
imgs = [re.sub(r"\s+\"[^\"]*\"\s*$", "", m).strip() for m in re.findall(r"!\[[^\]]*\]\(([^)]*)\)", btxt)]
tags = fm.get("tags") or []
if isinstance(tags, str): tags = [t.strip() for t in tags.strip("[]").split(",") if t.strip()]
tags = [re.sub(r"\s+", "", t.lstrip("#")) for t in tags]
tags = [t for t in tags if t]
meta = {"title": fm.get("title", ""), "category": fm.get("category", ""), "tags": ",".join(tags),
        "keyword": fm.get("keyword", ""), "variation": fm.get("variation", ""),
        "place": next((l.strip() for l in lines if re.match(r"^:::place\s", l)), ""),
        "images": len(imgs), "lines": len(btxt.splitlines()),
        "bad_images": [p for p in imgs if not os.path.isabs(p)],
        "missing_images": [p for p in imgs if os.path.isabs(p) and not os.path.isfile(p)]}
open(out + ".md", "w", encoding="utf-8").write(btxt)
json.dump(meta, open(out + ".json", "w", encoding="utf-8"), ensure_ascii=False)
'
JGET='import json,sys; v=json.load(open(sys.argv[1]))[sys.argv[2]]; print("\n".join(v) if isinstance(v,list) else v)'
meta() { python3 -c "$JGET" "$WORK/upload-meta.json" "$1"; }

log "시작 | $FINAL | blog-id=$BLOG_ID | dry-run=$DRY"

# 0) 표지 (대표이미지) — create-draft-from-folder 가 images/00-cover.* 를 본문 맨 앞에 넣고 대표로 지정한다
COVER="$POSTDIR/images/00-cover.png"
[ -f "$COVER" ] || die 12 "표지 images/00-cover.png 없음 — 이미지 단계(make_cover.py) 재실행"

# 1) lint (+ 이중 안전장치)
LINT_OUT="$(python3 "$HERE/lint_post.py" "$FINAL" --stage upload --json 2>"$WORK/lint.err")"; LINT_RC=$?
if [ "$LINT_RC" -ne 0 ]; then
  FAILS="$(printf '%s' "$LINT_OUT" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
    for c in d["checks"]:
        if c["result"]=="FAIL": print("  - %s: %s %s" % (c["id"], c["rule"], c["detail"]))
except Exception:
    print("  - lint 출력을 해석하지 못했습니다")
    sys.exit(1)')" || FAILS="$FAILS
$(sed 's/^/  | /' "$WORK/lint.err")"
  die 10 "lint_post.py 실패 — 업로드를 시작하지 않습니다.
$FAILS"
fi
PRE="$(python3 -c "$PYH" "$HERE" "$FINAL" precheck "$WORK/upload-meta")"; PRE_RC=$?
if [ "$PRE_RC" -ne 0 ]; then
  die 11 "이중 검사 실패 — 업로드를 시작하지 않습니다.
$(printf '%s\n' "$PRE" | sed 's/^/  - /')"
fi

# 3~4) frontmatter·본문
HELP_RC=0; python3 -c "$PYH" "$HERE" "$FINAL" body "$WORK/upload-meta" || HELP_RC=$?
[ "$HELP_RC" -eq 0 ] || die 2 "frontmatter 를 읽지 못했습니다."
TITLE="$(meta title)"; TAGS="$(meta tags)"; CATEGORY="$(meta category)"
NIMG="$(meta images)"; NLINES="$(meta lines)"; PLACE="$(meta place)"
[ -n "$CATEGORY_OPT" ] && [ -z "$CATEGORY" ] && CATEGORY="$CATEGORY_OPT"
[ -z "$CATEGORY" ] && CATEGORY="클라크중장비운전학원"
[ -n "$TITLE" ] || die 2 "frontmatter 에 title 이 없습니다."
BAD="$(meta bad_images)"; MISS="$(meta missing_images)"
if [ -n "$BAD" ]; then
  die 12 "이미지 경로가 절대경로가 아닙니다 (scripts/build_final.py 재실행):
$(printf '%s\n' "$BAD" | sed 's/^/  - /')"
fi
if [ -n "$MISS" ]; then
  die 12 "이미지 파일이 존재하지 않습니다:
$(printf '%s\n' "$MISS" | sed 's/^/  - /')"
fi
BODY="$WORK/body.md"; mv "$WORK/upload-meta.md" "$BODY"
mkdir -p "$WORK/images" && cp "$COVER" "$WORK/images/00-cover.png"

# 5) dry-run
if [ "$DRY" -eq 1 ]; then
  echo "[dry-run] 세션 확인 생략(dry-run)"
  echo "[dry-run] title: $TITLE"
  echo "[dry-run] category: $CATEGORY"
  echo "[dry-run] tags: $TAGS"
  echo "[dry-run] 본문 줄 수: $NLINES, 이미지 수: $NIMG"
  echo "[dry-run] 표지: $COVER"
  echo "[dry-run] 장소 지시문: $PLACE"
  log "dry-run 완료 | title=$TITLE | category=$CATEGORY | tags=$TAGS | 이미지=$NIMG"
  exit 0
fi

# 2) 세션 확인 (종료 코드 아닌 stdout 문구로 판정; dry-run 은 위에서 이미 종료)
if ! command -v naver-blog-cli >/dev/null 2>&1; then
  die 20 "naver-blog-cli 를 찾을 수 없습니다. /clark-blog:blog-setup 으로 설치를 확인하세요."
fi
SESS="$(NAVER_BLOG_ID="$BLOG_ID" naver-blog-cli check-session 2>&1)"
case "$SESS" in
  "세션 정상"*"글쓰기 가능"*) ;;
  *) die 20 "네이버 세션을 사용할 수 없습니다: $(printf '%s' "$SESS" | head -n1)
작업 폴더에서 터미널로 직접 로그인하세요 (\"로그인 상태 유지\" 체크):
  NAVER_STATE=\"\$PWD/playwright-state/storage_state.json\" \"\$(uv tool dir)/naver-blog-cli/bin/python\" ~/naver-blog-cli/login_setup.py" ;;
esac

# 6) 임시저장 (create-draft-from-folder: 표지를 본문 맨 앞에 넣고 대표 지정)
CREATE="$(NAVER_BLOG_ID="$BLOG_ID" naver-blog-cli create-draft-from-folder "$WORK" --markdown-file body.md --title="$TITLE" --category="$CATEGORY" --tags="$TAGS" 2>&1)"
case "$CREATE" in
  *"넣기 전에 걸린 것"*|*"작성 실패"*|*"임시저장이 안 된 것 같습니다"*|*"못 찾음"*) CREATE_BAD=1 ;;
  *"임시저장 완료"*) CREATE_BAD=0 ;;
  *) CREATE_BAD=1 ;;
esac
case "$CREATE_BAD" in
  0) ;;
  *) die 30 "임시저장에 실패했습니다 (naver-blog-cli 출력):
$(printf '%s\n' "$CREATE" | tail -n 5 | sed 's/^/  | /')
references/naver-blog-cli.md 의 실패 유형(넣기 전에 걸린 것·에디터 변경·이미지 10MB·세션 만료)을 확인하세요." ;;
esac
WARN=""
case "$CREATE" in
  *"설정 실패"*) WARN="경고: 카테고리/태그 설정 실패 — 네이버 임시저장 글에서 직접 확인"
                 echo "$WARN" >&2
                 log "경고 | 설정 실패 포함: $(printf '%s' "$CREATE" | grep '설정 실패' | head -n1)" ;;
esac
if [[ "$CREATE" == *"대표 지정 실패"* || "$CREATE" == *"표지 넣기 실패"* ]]; then
  echo "경고: 대표이미지 지정 실패 — 임시저장 글에서 첫 이미지를 대표로 직접 지정" >&2
  log "경고 | 대표이미지 지정 실패: $(printf '%s' "$CREATE" | grep -E '대표 지정 실패|표지 넣기 실패' | head -n1)"
elif ! { [[ "$CREATE" == *"0:표지"* ]] && [[ "$CREATE" =~ (^|[^[:alnum:]])대표\ 지정($|[^[:alnum:]]) ]]; }; then
  echo "경고: 대표이미지 지정 확인 불가 — 임시저장 글에서 확인" >&2
  log "경고 | 대표이미지 지정 확인 불가 (0:표지 또는 대표 지정 노트 없음)"
fi
PLACE_PICKED="$(printf '%s\n' "$CREATE" | perl -CSD -Mutf8 -ne 'if (/\d+:장소\((.*?)\)(?:, |\])/) { print $1; exit }')"
if [ -z "$PLACE_PICKED" ]; then
  echo "경고: 장소 카드 확인 필요 — 장소(…) 노트 없음 또는 빈 값" >&2
  log "경고 | 장소 카드 확인 필요: 장소 노트 없음/빈 값"
else
  case "$PLACE_PICKED" in
    *클라크*) ;;
    *) echo "경고: 장소 카드 확인 필요 — $PLACE_PICKED" >&2
       log "경고 | 장소 카드 확인 필요: $PLACE_PICKED" ;;
  esac
fi

# 7) 확인
DRAFTS="$(NAVER_BLOG_ID="$BLOG_ID" naver-blog-cli list-drafts 2>&1)"
HIT="$(printf '%s\n' "$DRAFTS" | grep -F -- "$TITLE" | head -n1)"
if [ -z "$HIT" ]; then
  die 31 "임시저장 목록에서 제목을 확인하지 못했습니다. 저장은 됐을 수 있으니 네이버에서 직접 확인하세요 (글쓰기 → 임시저장 글)."
fi

# 8) 성공
log "성공 | title=$TITLE | category=$CATEGORY | tags=$TAGS | 이미지=$NIMG | 장소=${PLACE_PICKED:-} | variation=$(meta variation) | list-drafts: $HIT"
echo "임시저장 완료 — 네이버 앱/웹 → 글쓰기 → 임시저장 글 → 미리보기 → 발행"
echo "  제목: $TITLE"
echo "  카테고리: $CATEGORY / 태그: $TAGS / 이미지: ${NIMG}장"
[ -n "$PLACE_PICKED" ] && echo "  장소: $PLACE_PICKED"
[ -n "$WARN" ] && echo "$WARN"
exit 0
