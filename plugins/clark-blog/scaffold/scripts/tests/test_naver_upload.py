import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
DESIGN = "# 디자인 시스템\n\n<!-- lint: min_chars=900 max_chars=6000 min_h2=3 max_h2=5 min_images=2 min_sources=1 tags_min=3 tags_max=6 -->\n"
PROFILE = "# 학원\n\n## 금칙어\n\n- `실기시험장`\n"

TITLE = "지게차운전기능사 실기 순서, 처음이라면 이렇게 준비하세요"
STUB = """#!/usr/bin/env bash
echo "$* | id=${NAVER_BLOG_ID:-}" >> "$STUB_LOG"
case "$1" in
  check-session)
    if [ "${STUB_SESSION:-ok}" = ok ]; then echo "세션 정상 (https://blog.naver.com/x, 글쓰기 가능)";
    else echo "확인 실패: 세션 파일 없음: playwright-state/storage_state.json"; echo "python login_setup.py 를 먼저 실행해서 직접 로그인하세요."; fi ;;
  create-draft)
    while [ $# -gt 0 ]; do [ "$1" = --file ] && cp "$2" "$STUB_BODY"; shift; done
    if [ "${STUB_CREATE:-ok}" = ok ]; then echo "임시저장 완료: 제목"; else echo "임시저장 버튼을 못 찾음 (에디터 변경?)"; fi ;;
  list-drafts)
    if [ "${STUB_LIST:-ok}" = ok ]; then echo "$STUB_TITLE  (2026-10-06)"; else echo "임시저장된 글이 없습니다"; fi ;;
esac
exit 0
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
        self.post = os.path.join(r, "work", "posts", "001-test")
        os.makedirs(self.post)
        self.log = os.path.join(r, "stub.log")
        self.sbody = os.path.join(r, "stub-body.md")
        self.img = os.path.join(self.post, "img1.png")
        open(self.img, "wb").close()
        self.final = os.path.join(self.post, "final.md")
        self.write_final(self.sample())

    def tearDown(self):
        self._tmp.cleanup()

    def sample(self, img=None, extra=""):
        imgs = [img or self.img, self.img, self.img]
        secs = []
        for s in range(4):
            sents = " ".join(f"지게차 실습은 순서를 익히면 차분하게 해낼 수 있습니다 {s}-{i}." for i in range(14))
            src = f" (출처: https://www.law.go.kr/s{s})" if s < 2 else ""
            h2 = "지게차 운전기능사 소제목 1" if s == 0 else f"소제목 {s + 1}"
            sec = f"## {h2}\n\n**핵심** 지게차 운전기능사 {sents}{src}\n\n> 한 줄 요약\n"
            if s < 3:
                sec += f"\n![캡션{s + 1}]({imgs[s]})\n"
            secs.append(sec)
        secs[3] += ("\n[관련글1](https://blog.naver.com/pajuclark/1)\n"
                    "[관련글2](https://blog.naver.com/pajuclark/2)\n" + extra)
        fm = (f"---\ntitle: {TITLE}\nkeyword: 지게차 운전기능사\ncategory: 클라크중장비운전학원\n"
              "tags: [지게차운전기능사, 지게차실기, 의정부지게차학원, 양주지게차학원, 국비지원]\n"
              "variation: {structure: 절차형, intro: 상황, region: [의정부, 양주], cta: 관련글}\n---\n")
        return (fm + "<!-- 제목 B안: 다른 제목 후보 -->\n\n# 지게차운전기능사 실기 순서\n\n" + "\n".join(secs))

    def write_final(self, text):
        with open(self.final, "w", encoding="utf-8") as f:
            f.write(text)

    def run_script(self, *args, **env):
        e = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], STUB_LOG=self.log,
                 STUB_BODY=self.sbody, STUB_TITLE=TITLE, TMPDIR=self.root)
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
        self.assertIn("이미지 수: 3", p.stdout)
        self.assertNotIn("create-draft", self.stub_calls())

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

    def test_session_failure_exit_20(self):
        p = self.run_script(STUB_SESSION="fail")
        self.assertEqual(p.returncode, 20, p.stderr)
        self.assertIn("확인 실패", p.stderr)
        self.assertIn("login_setup.py", p.stderr)
        self.assertNotIn("create-draft", self.stub_calls())

    def test_success_flow(self):
        p = self.run_script("--blog-id", "myblog")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("임시저장 완료", p.stdout)
        calls = self.stub_calls()
        self.assertIn("id=myblog", calls)
        self.assertIn("create-draft --title " + TITLE, calls)
        self.assertIn("--category 클라크중장비운전학원", calls)
        with open(self.sbody, encoding="utf-8") as f:
            body = f.read()
        self.assertNotIn("제목 B안", body)
        self.assertNotIn("\n# ", "\n" + body)
        self.assertNotIn("title:", body)
        self.assertIn("## 소제목 2", body)
        with open(os.path.join(self.post, "upload.log"), encoding="utf-8") as f:
            log = f.read()
        self.assertIn("성공", log)
        self.assertIn(TITLE, log)
        leftovers = [n for n in os.listdir(self.root) if n.startswith("naver-upload.")]
        self.assertEqual(leftovers, [])

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
