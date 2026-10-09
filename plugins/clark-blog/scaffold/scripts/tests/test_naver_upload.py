import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
DESIGN = "# 디자인 시스템\n\n<!-- lint: min_chars=900 max_chars=6000 min_h2=3 max_h2=5 min_images=2 min_sources=1 tags_min=3 tags_max=6 -->\n"
PROFILE = "# 학원\n\n## 금칙어\n\n- `실기시험장`\n"

TITLE = "의정부 지게차운전기능사 실기 순서, 처음이라면 이렇게 준비하세요"
PLACE = "클라크중장비운전학원 양주시 백석읍"
STUB = """#!/usr/bin/env bash
echo "$* | id=${NAVER_BLOG_ID:-} | ro=NAVER_BLOG_READONLY=${NAVER_BLOG_READONLY:-}" >> "$STUB_LOG"
case "$1" in
  check-session)
    if [ "${STUB_SESSION:-ok}" = ok ]; then echo "세션 정상 (https://blog.naver.com/x, 글쓰기 가능)";
    else echo "확인 실패: 세션 파일 없음: playwright-state/storage_state.json"; echo "python login_setup.py 를 먼저 실행해서 직접 로그인하세요."; fi ;;
  create-draft-from-folder)
    shift
    FOLDER="$1"; shift
    MD=post.md
    while [ $# -gt 0 ]; do case "$1" in --markdown-file) MD="$2"; shift ;; esac; shift; done
    cp "$FOLDER/$MD" "$STUB_BODY"
    if [ -f "$FOLDER/images/00-cover.png" ]; then echo "cover-present" >> "$STUB_LOG"; fi
    case "${STUB_CREATE:-ok}" in
      ok) echo "임시저장 완료: 제목 [0:표지, 1:이미지, 2:이미지, 3:이미지, 4:장소(클라크중장비운전학원 양주시 백석읍), 대표 지정, 카테고리=클라크중장비운전학원, 태그 5개]" ;;
      warn) echo "임시저장 완료: 제목 [0:표지, 대표 지정, 설정 실패(카테고리)]" ;;
      rep) echo "임시저장 완료: 제목 [0:표지, 1:이미지, 4:장소(클라크중장비운전학원 양주시 백석읍), 대표 지정 실패, 카테고리=x]" ;;
      cover) echo "임시저장 완료: 제목 [0:표지 넣기 실패(timeout), 4:장소(클라크중장비운전학원 양주시 백석읍), 카테고리=x]" ;;
      norep) echo "임시저장 완료: 제목 [0:표지, 4:장소(클라크중장비운전학원 양주시), 카테고리=x]" ;;
      noplace) echo "임시저장 완료: 제목 [0:표지, 대표 지정, 카테고리=x]" ;;
      place) echo "임시저장 완료: 제목 [0:표지, 4:장소(다른학원 서울), 대표 지정, 카테고리=x]" ;;
      mixed) echo "임시저장 완료: 제목 [작성 실패: x]" ;;
      preflight) printf '넣기 전에 걸린 것 (아무것도 하지 않았습니다):\n- 이미지 없음: /x.png\n' ;;
      other) echo "알 수 없는 출력" ;;
      *) echo "임시저장 버튼을 못 찾음 (에디터 변경?)" ;;
    esac ;;
  list-drafts)
    if [ "${STUB_LIST:-ok}" = ok ]; then echo "$STUB_TITLE  (2026-10-06)"; else echo "임시저장된 글이 없습니다"; fi ;;
esac
exit 0
"""
# `uv tool dir` -> $STUB_UVDIR ; $STUB_UVDIR/naver-blog-cli/bin/python 은 check_blog_account.py 대역
UV_STUB = """#!/usr/bin/env bash
[ "$1 $2" = "tool dir" ] && echo "$STUB_UVDIR"
exit 0
"""
PY_STUB = """#!/usr/bin/env bash
echo "account-check $(basename "$1") $2" >> "$STUB_LOG"
echo "DeprecationWarning: stderr 소음이 결과 줄보다 먼저 나올 수 있다" >&2
case "${STUB_ACCOUNT:-ok}" in
  ok) echo "계정 확인: $2 블로그 글쓰기 가능 — 글쓰기 화면 https://blog.naver.com/$2?Redirect=Write"; exit 0 ;;
  other) echo "로그인한 계정이 $2 블로그에 글을 쓸 수 없음 — 글쓰기 화면이 https://blog.naver.com/iloveccmel 로 이동 (로그인 계정의 블로그: iloveccmel)"; exit 21 ;;
  *) echo "계정 확인 실패 — TimeoutError: x"; exit 22 ;;
esac
"""


class NaverUploadTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        r = self.root = self._tmp.name
        shutil.copytree(SCRIPTS, os.path.join(r, "scripts"),
                        ignore=shutil.ignore_patterns("tests", "__pycache__"))
        kd = os.path.join(r, "knowledge")
        os.makedirs(kd)
        for name, body in (("design-system.md", DESIGN), ("academy-profile.md", PROFILE)):
            with open(os.path.join(kd, name), "w", encoding="utf-8") as f:
                f.write(body)
        self.bin = os.path.join(r, "bin")
        os.makedirs(self.bin)
        stub = os.path.join(self.bin, "naver-blog-cli")
        with open(stub, "w", encoding="utf-8") as f:
            f.write(STUB)
        os.chmod(stub, 0o755)
        self.uvdir = os.path.join(r, "uvtools")
        os.makedirs(os.path.join(self.uvdir, "naver-blog-cli", "bin"))
        for path, body in ((os.path.join(self.bin, "uv"), UV_STUB),
                           (os.path.join(self.uvdir, "naver-blog-cli", "bin", "python"), PY_STUB)):
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            os.chmod(path, 0o755)
        self.post = os.path.join(r, "work", "posts", "001-test")
        os.makedirs(self.post)
        self.log = os.path.join(r, "stub.log")
        self.sbody = os.path.join(r, "stub-body.md")
        self.img = os.path.join(self.post, "img1.png")
        open(self.img, "wb").close()
        self.intro = os.path.join(self.post, "학원소개.png")
        open(self.intro, "wb").close()
        os.makedirs(os.path.join(self.post, "images"))
        self.cover = os.path.join(self.post, "images", "00-cover.png")
        open(self.cover, "wb").close()
        self.final = os.path.join(self.post, "final.md")
        self.write_final(self.sample())

    def tearDown(self):
        self._tmp.cleanup()

    def sample(self, img=None, extra="", tail=None):
        imgs = [img or self.img, self.img, self.img]
        F = "\u3164"
        secs = []
        for n in range(4):
            sents = " ".join(f"지게차 실습은 순서를 익히면 차분하게 해낼 수 있습니다 {n}-{i}." for i in range(14))
            h2 = "지게차 운전기능사 소제목 1" if n == 0 else f"소제목 {n + 1}"
            sec = f"{F}\n\n## {n + 1}\ufe0f\u20e3 {h2}\n\n**핵심** 지게차 운전기능사 {sents}\n"
            if n < 3:
                sec += f"\n![]({imgs[n]})\n"
            secs.append(sec)
        closing = (tail if tail is not None else
                   "[관련글1](https://blog.naver.com/pajuclark/1)\n[관련글2](https://blog.naver.com/pajuclark/2)\n\n"
                   f"{F}\n\n## 📞 문의 및 수강신청: 031-855-9948\n\n![]({self.intro})\n"
                   f":::place 클라크중장비운전학원:::\n\n**#지게차운전기능사 #지게차실기 #의정부지게차학원 #양주지게차학원 #국비지원**\n")
        fm = (f"---\ntitle: {TITLE}\nkeyword: 지게차 운전기능사\ncategory: 클라크중장비운전학원\n"
              "tags: [지게차운전기능사, 지게차실기, 의정부지게차학원, 양주지게차학원, 국비지원]\n"
              "variation: {type: 정보, structure: 절차형, intro: 상황, region: [의정부, 양주], title_region: 의정부}\n---\n")
        toc = "\u3164\n\n## 📑 목차\n- 소제목 1\n- 소제목 2\n- 소제목 3\n- 소제목 4\n\n---\n\n"
        return (fm + "<!-- 제목 B안: 다른 제목 후보 -->\n\n# 지게차운전기능사 실기 순서\n\n도입 문단입니다.\n\n" + toc
                + "\n".join(secs) + extra + "\n" + closing)

    def write_final(self, text):
        with open(self.final, "w", encoding="utf-8") as f:
            f.write(text)

    def run_script(self, *args, **env):
        e = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], STUB_LOG=self.log,
                 STUB_BODY=self.sbody, STUB_TITLE=TITLE, TMPDIR=self.root,
                 STUB_UVDIR=self.uvdir)
        e.update(env)
        return subprocess.run(["bash", os.path.join(self.root, "scripts", "naver_upload.sh"), self.final, *args],
                              cwd=self.root, env=e, capture_output=True, text=True)

    def stub_calls(self):
        if not os.path.exists(self.log):
            return ""
        with open(self.log, encoding="utf-8") as f:
            return f.read()

    def test_lint_failure_exit_10(self):
        self.write_final(self.sample().replace("소제목 2", "소제목 2 [출처 필요]"))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("lint_post.py 실패", p.stderr)
        self.assertEqual(self.stub_calls(), "")

    def test_double_check_exit_11(self):
        # lint 를 무력화(항상 통과)해도 셸의 이중 검사가 금칙어를 잡는다
        lp = os.path.join(self.root, "scripts", "lint_post.py")
        with open(lp, encoding="utf-8") as f:
            src = f.read()
        marker = 'if __name__ == "__main__":\n    sys.exit(main())'
        self.assertIn(marker, src)
        with open(lp, "w", encoding="utf-8") as f:
            f.write(src.replace(marker, 'if __name__ == "__main__":\n    sys.exit(0)'))
        self.write_final(self.sample(extra="\n실기시험장 안내\n"))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 11, p.stderr)
        self.assertIn("금칙어: 실기시험장", p.stderr)
        self.assertEqual(self.stub_calls(), "")

    def test_dry_run_prints_values(self):
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(f"title: {TITLE}", p.stdout)
        self.assertIn("tags: 지게차운전기능사,지게차실기,의정부지게차학원,양주지게차학원,국비지원", p.stdout)
        self.assertIn("이미지 수: 4", p.stdout)  # 본문 3 + 학원소개 1 (표지는 본문 밖)
        self.assertIn("표지: " + self.cover, p.stdout)
        self.assertIn("장소 지시문: :::place 클라크중장비운전학원:::", p.stdout)
        self.assertNotIn("create-draft-from-folder", self.stub_calls())

    def test_relative_image_blocked_by_lint(self):
        self.write_final(self.sample(img="images/01-cover.png"))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 10, p.stderr)
        self.assertIn("image_paths", p.stderr)

    def test_non_absolute_image_exit_12(self):
        # lint 는 URL 이미지를 통과시키지만 naver-blog-cli 는 로컬 경로만 받는다 -> 셸이 12 로 막는다
        self.write_final(self.sample(img="https://example.com/a.png"))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 12, p.stderr)
        self.assertIn("절대경로", p.stderr)
        self.assertIn("https://example.com/a.png", p.stderr)

    def test_missing_option_value_exit_2(self):
        for opt in ("--blog-id", "--category"):
            p = subprocess.run(["bash", os.path.join(self.root, "scripts", "naver_upload.sh"), self.final, opt],
                               cwd=self.root, capture_output=True, text=True, timeout=20)
            self.assertEqual(p.returncode, 2, p.stderr)
            self.assertIn("값이 필요합니다", p.stderr)

    def test_dry_run_skips_session(self):
        p = self.run_script("--dry-run", STUB_SESSION="fail")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("세션 확인 생략", p.stdout)
        self.assertNotIn("check-session", self.stub_calls())
        self.assertNotIn("account-check", self.stub_calls())

    def test_dry_run_image_exit_12_without_login(self):
        self.write_final(self.sample(img="https://example.com/a.png"))
        p = self.run_script("--dry-run", STUB_SESSION="fail")
        self.assertEqual(p.returncode, 12, p.stderr)

    def test_setting_failure_warning_in_stdout(self):
        p = self.run_script(STUB_CREATE="warn")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("경고: 카테고리/태그 설정 실패 — 네이버 임시저장 글에서 직접 확인", p.stdout)

    def test_failure_phrase_overrides_success_phrase(self):
        p = self.run_script(STUB_CREATE="mixed")
        self.assertEqual(p.returncode, 30, p.stderr)

    def test_session_failure_exit_20(self):
        p = self.run_script(STUB_SESSION="fail")
        self.assertEqual(p.returncode, 20, p.stderr)
        self.assertIn("확인 실패", p.stderr)
        self.assertIn("login_setup.py", p.stderr)
        self.assertNotIn("create-draft-from-folder", self.stub_calls())

    def test_account_mismatch_exit_21(self):
        # 2026-10-09: 다른 계정(iloveccmel) 세션이 check-session 은 통과했지만 글쓰기 화면이 그 블로그로 리다이렉트
        p = self.run_script(STUB_ACCOUNT="other")
        self.assertEqual(p.returncode, 21, p.stderr)
        self.assertIn("로그인한 계정이 pajuclark 블로그에 글을 쓸 수 없음 — 그 블로그 계정으로 login_setup.py 다시 실행", p.stderr)
        self.assertIn("확인 결과: 로그인한 계정이 pajuclark 블로그에 글을 쓸 수 없음 — 글쓰기 화면이 https://blog.naver.com/iloveccmel", p.stderr)
        self.assertIn("pajuclark 블로그 계정으로 직접 로그인", p.stderr)
        calls = self.stub_calls()
        self.assertIn("account-check check_blog_account.py pajuclark", calls)
        self.assertNotIn("create-draft-from-folder", calls)
        self.assertNotIn("list-drafts", calls)
        with open(os.path.join(self.post, "upload.log"), encoding="utf-8") as f:
            self.assertIn("exit 21", f.read())

    def test_account_check_error_exit_20(self):
        p = self.run_script(STUB_ACCOUNT="error")
        self.assertEqual(p.returncode, 20, p.stderr)
        self.assertIn("계정 확인 실패(exit 22)", p.stderr)
        self.assertNotIn("create-draft-from-folder", self.stub_calls())

    def test_account_check_without_cli_python_exit_20(self):
        os.remove(os.path.join(self.uvdir, "naver-blog-cli", "bin", "python"))
        p = self.run_script()
        self.assertEqual(p.returncode, 20, p.stderr)
        self.assertIn("계정 확인용 python", p.stderr)
        self.assertNotIn("create-draft-from-folder", self.stub_calls())

    def test_success_flow(self):
        p = self.run_script("--blog-id", "myblog")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("임시저장 완료", p.stdout)
        calls = self.stub_calls()
        self.assertIn("id=myblog", calls)
        self.assertIn("account-check check_blog_account.py myblog", calls)
        self.assertLess(calls.index("check-session"), calls.index("account-check"))
        self.assertLess(calls.index("account-check"), calls.index("create-draft-from-folder"))
        self.assertIn("create-draft-from-folder ", calls)
        self.assertIn("--markdown-file body.md", calls)
        self.assertIn("--title=" + TITLE, calls)
        self.assertIn("--tags=지게차운전기능사,지게차실기,의정부지게차학원,양주지게차학원,국비지원", calls)
        self.assertIn("cover-present", calls)   # $WORK/images/00-cover.png 가 복사돼 있었다
        self.assertIn("장소: 클라크중장비운전학원 양주시 백석읍", p.stdout)
        self.assertNotIn("경고", p.stderr)
        self.assertIn("--category=클라크중장비운전학원", calls)
        self.assertNotIn("publish-draft", calls)
        self.assertNotIn("delete-", calls)
        self.assertIn("NAVER_BLOG_READONLY=1", calls)
        with open(self.sbody, encoding="utf-8") as f:
            body = f.read()
        self.assertNotIn("제목 B안", body)
        self.assertNotIn("\n# ", "\n" + body)
        self.assertNotIn("title:", body)
        self.assertIn("## 2\ufe0f\u20e3 소제목 2", body)
        self.assertIn("\u3164\n\n## 1\ufe0f\u20e3", body)        # ㅤ 여백 줄 + 빈 줄 보존
        self.assertIn(":::place 클라크중장비운전학원:::", body)
        self.assertIn("\n**#지게차운전기능사 ", body)                # 해시태그 줄 보존
        self.assertNotIn("00-cover", body)                          # 표지는 본문이 아니라 폴더 images/ 로
        with open(os.path.join(self.post, "upload.log"), encoding="utf-8") as f:
            log = f.read()
        self.assertIn("성공", log)
        self.assertIn("장소=클라크중장비운전학원 양주시 백석읍", log)
        self.assertIn(TITLE, log)
        leftovers = [n for n in os.listdir(self.root) if n.startswith("naver-upload.")]
        self.assertEqual(leftovers, [])

    def test_cover_missing_exit_12(self):
        os.remove(self.cover)
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 12, p.stderr)
        self.assertIn("표지 images/00-cover.png 없음", p.stderr)
        self.assertIn("make_cover.py", p.stderr)
        self.assertEqual(self.stub_calls(), "")

    def test_rep_image_failure_warning(self):
        for mode in ("rep", "cover"):
            os.path.exists(self.log) and os.remove(self.log)
            p = self.run_script(STUB_CREATE=mode)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("경고: 대표이미지 지정 실패 — 임시저장 글에서 첫 이미지를 대표로 직접 지정", p.stderr)
            with open(os.path.join(self.post, "upload.log"), encoding="utf-8") as f:
                self.assertIn("대표이미지 지정 실패", f.read())

    def test_place_warning_when_not_clark(self):
        p = self.run_script(STUB_CREATE="place")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("경고: 장소 카드 확인 필요 — 다른학원 서울", p.stderr)
        self.assertIn("장소: 다른학원 서울", p.stdout)

    def test_precheck_leftover_source_exit_11(self):
        self._neuter_lint()
        self.write_final(self.sample(extra="\n지게차는 중요합니다 출처: https://x.kr\n"))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 11, p.stderr)
        self.assertEqual(self.stub_calls(), "")

    def _neuter_lint(self):
        lp = os.path.join(self.root, "scripts", "lint_post.py")
        with open(lp, encoding="utf-8") as f:
            src = f.read()
        marker = 'if __name__ == "__main__":\n    sys.exit(main())'
        with open(lp, "w", encoding="utf-8") as f:
            f.write(src.replace(marker, 'if __name__ == "__main__":\n    sys.exit(0)'))

    def test_precheck_source_leftover_exit_11(self):
        self._neuter_lint()
        self.write_final(self.sample(extra="\n지게차는 중요합니다 (출처: https://x.kr)\n"))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 11, p.stderr)
        self.assertIn("출처: 잔존", p.stderr)
        self.assertIn("scripts/build_final.py 재실행", p.stderr)

    def test_precheck_caption_leftover_exit_11(self):
        self._neuter_lint()
        self.write_final(self.sample().replace(f"![]({self.img})", f"![캡션]({self.img})", 1))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 11, p.stderr)
        self.assertIn("alt(캡션) 있는 이미지", p.stderr)

    def test_precheck_missing_place_and_hashtag_exit_11(self):
        self._neuter_lint()
        self.write_final(self.sample(tail="## 📞 문의 및 수강신청: 031-855-9948\n"))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 11, p.stderr)
        self.assertIn(":::place 지시문 없음", p.stderr)
        self.assertIn("**# 해시태그 줄 없음", p.stderr)

    def test_precheck_link_source_exit_11(self):
        self._neuter_lint()
        self.write_final(self.sample(extra="\n지게차는 중요합니다 [출처](https://x.kr)\n"))
        p = self.run_script("--dry-run")
        self.assertEqual(p.returncode, 11, p.stderr)
        self.assertIn("[출처]( 링크형", p.stderr)

    def test_rep_unconfirmed_warning(self):
        p = self.run_script(STUB_CREATE="norep")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("경고: 대표이미지 지정 확인 불가 — 임시저장 글에서 확인", p.stderr)

    def test_place_missing_warning(self):
        p = self.run_script(STUB_CREATE="noplace")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("경고: 장소 카드 확인 필요", p.stderr)

    def test_tags_normalized(self):
        txt = self.sample().replace("tags: [지게차운전기능사, 지게차실기, 의정부지게차학원, 양주지게차학원, 국비지원]",
                                    "tags: [#지게차운전기능사, 지게차 실기, 의정부지게차학원, 양주지게차학원, 국비지원]")
        self.write_final(txt)
        p = self.run_script()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("--tags=지게차운전기능사,지게차실기,의정부지게차학원", self.stub_calls())

    def test_preflight_failure_exit_30(self):
        p = self.run_script(STUB_CREATE="preflight")
        self.assertEqual(p.returncode, 30, p.stderr)
        self.assertIn("넣기 전에 걸린 것", p.stderr)

    def test_unknown_output_exit_30(self):
        p = self.run_script(STUB_CREATE="other")
        self.assertEqual(p.returncode, 30, p.stderr)

    def test_create_failure_exit_30(self):
        p = self.run_script(STUB_CREATE="fail")
        self.assertEqual(p.returncode, 30, p.stderr)
        self.assertIn("못 찾음", p.stderr)

    def test_list_missing_exit_31(self):
        p = self.run_script(STUB_LIST="none")
        self.assertEqual(p.returncode, 31, p.stderr)
        self.assertIn("직접 확인", p.stderr)


if __name__ == "__main__":
    unittest.main()
