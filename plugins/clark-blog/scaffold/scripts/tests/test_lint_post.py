import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "lint_post.py")
sys.path.insert(0, os.path.dirname(HERE))
import lint_post  # noqa: E402

DESIGN = "# 디자인 시스템\n\n<!-- lint: min_chars=900 max_chars=6000 min_h2=3 max_h2=5 min_images=2 min_sources=1 tags_min=3 tags_max=6 -->\n"
PROFILE = "# 학원\n\n## 금칙어\n\n- `실기시험장` — 변형 `실기 시험장`, `실기시험 장소`도 금지\n- `무관한단어`\n\n## 다음 절\n\n- `섹션밖단어`\n"


class LintPostTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = cls._tmp.name
        kd = os.path.join(cls.root, "knowledge")
        os.makedirs(kd)
        for name, body in (("design-system.md", DESIGN), ("academy-profile.md", PROFILE)):
            with open(os.path.join(kd, name), "w", encoding="utf-8") as f:
                f.write(body)
        cls.imgs = []
        for i in range(1, 4):
            p = os.path.join(cls.root, f"img{i}.png")
            open(p, "wb").close()
            cls.imgs.append(p)
        sections = []
        for s in range(4):
            sents = " ".join(f"지게차 실습은 순서를 익히면 차분하게 해낼 수 있습니다 {s}-{i}." for i in range(14))
            src = f" (출처: https://www.law.go.kr/s{s})" if s < 2 else ""
            sections.append(f"## 소제목 {s + 1}\n\n**핵심** {sents}{src}\n\n> 한 줄 요약\n")
        sections[0] += f"\n![캡션1]({cls.imgs[0]})\n"
        sections[1] += f"\n![캡션2]({cls.imgs[1]})\n"
        sections[2] += f"\n![캡션3]({cls.imgs[2]})\n"
        sections[3] += ("\n[관련글1](https://blog.naver.com/pajuclark/1)\n"
                        "[관련글2](https://blog.naver.com/pajuclark/2)\n")
        cls.body = "# 지게차운전기능사 실기 순서\n\n" + "\n".join(sections)
        cls.fm = ("---\ntitle: 지게차운전기능사 실기 순서\nkeyword: 지게차 운전기능사\ncategory: 클라크중장비운전학원\n"
                  "tags: [지게차운전기능사, 지게차실기, 의정부지게차학원, 양주지게차학원, 국비지원]\n"
                  "variation: {structure: 절차형, intro: 상황}\n---\n")
        cls.good = cls.fm + cls.body

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def write(self, name, text):
        p = os.path.join(self.root, name)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def run_lint(self, text, stage="final", name="post.md"):
        res, _ = lint_post.lint_file(self.write(name, text), stage)
        return res

    def failed(self, res):
        return sorted(c["id"] for c in res["checks"] if c["result"] == "FAIL")

    def test_good_final_passes(self):
        res = self.run_lint(self.good)
        self.assertEqual(self.failed(res), [], res)
        self.assertTrue(res["pass"])
        self.assertEqual(res["stats"]["images"], 3)

    def test_cli_exit_codes_and_json(self):
        ok = self.write("ok.md", self.good)
        r = subprocess.run([sys.executable, SCRIPT, ok, "--stage", "final", "--json"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue(json.loads(r.stdout)["pass"])
        bad = self.write("bad.md", self.good + "\n실기 시험장 안내\n")
        r = subprocess.run([sys.executable, SCRIPT, bad, "--stage", "final"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("forbidden", r.stdout)
        r = subprocess.run([sys.executable, SCRIPT, os.path.join(self.root, "none.md"), "--stage", "final"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_forbidden_with_space_variant(self):
        res = self.run_lint(self.good + "\n여기가 실기 시험장 입니다\n")
        self.assertEqual(self.failed(res), ["forbidden"])
        detail = next(c["detail"] for c in res["checks"] if c["id"] == "forbidden")
        self.assertRegex(detail, r"줄 \d+")

    def test_related_placeholder_left(self):
        res = self.run_lint(self.good + "\n[[관련글]]\n")
        self.assertEqual(self.failed(res), ["related_links"])

    def test_empty_image(self):
        res = self.run_lint(self.good.replace(self.imgs[0], ""))
        self.assertEqual(self.failed(res), ["image_paths"])

    def test_frontmatter_missing_key(self):
        res = self.run_lint(self.good.replace("category: 클라크중장비운전학원\n", ""))
        self.assertEqual(self.failed(res), ["frontmatter"])

    def test_source_placeholder(self):
        res = self.run_lint(self.good + "\n수강료는 얼마입니다 [출처 필요]\n")
        self.assertEqual(self.failed(res), ["placeholder_sources"])

    def test_draft_without_frontmatter_passes(self):
        slot_body = self.body.replace(self.imgs[0], "").replace(self.imgs[1], "").replace(self.imgs[2], "")
        slot_body = slot_body.replace("![캡션1]()", "![슬롯: 교육장]()").replace("![캡션2]()", "![슬롯: 실습]()")
        res = self.run_lint(slot_body, stage="draft")
        self.assertEqual(self.failed(res), [], res)
        by = {c["id"]: c["result"] for c in res["checks"]}
        self.assertEqual(by["variation"], "SKIP")
        for cid in ("frontmatter", "title_keyword", "tags_count", "related_links", "image_paths", "h1_once"):
            self.assertEqual(by[cid], "SKIP")

    def test_defaults_without_knowledge(self):
        th = lint_post.load_thresholds(None)
        fw = lint_post.load_forbidden(None)
        self.assertEqual(th["min_chars"], 1500)
        self.assertIn("실기 시험장", fw)
        res = lint_post.lint_text("## a\n실기시험 장소 안내\n", "draft", th, fw)
        self.assertIn("forbidden", self.failed(res))

    def test_headings_inside_code_fence_ignored(self):
        res = self.run_lint(self.good + "\n```\n## 코드 안 제목\n# 코드 안 h1\n```\n")
        self.assertEqual(self.failed(res), [])
        self.assertEqual(res["stats"]["h2_count"], 4)

    def test_loaders_apply_custom_values(self):
        kd = os.path.join(self.root, "knowledge")
        th = lint_post.load_thresholds(kd)
        self.assertEqual((th["min_chars"], th["max_h2"], th["tags_min"]), (900, 5, 3))
        fw = lint_post.load_forbidden(kd)
        self.assertIn("무관한단어", fw)
        self.assertNotIn("섹션밖단어", fw)
        self.assertEqual(self.failed(self.run_lint(self.good + "\n무관한단어\n")), ["forbidden"])
        self.assertEqual(self.failed(self.run_lint(self.good + "\n섹션밖단어\n")), [])

    def test_chars_fail(self):
        self.assertEqual(self.failed(self.run_lint(self.good + "\n" + "가" * 6000 + "\n")), ["chars"])

    def test_h2_fail(self):
        self.assertEqual(self.failed(self.run_lint(self.good + "\n## 다섯\n\n## 여섯\n")), ["h2_count"])

    def test_images_fail(self):
        t = self.good.replace(f"![캡션2]({self.imgs[1]})", "").replace(f"![캡션3]({self.imgs[2]})", "")
        self.assertEqual(self.failed(self.run_lint(t)), ["images"])

    def test_sources_fail(self):
        t = self.good.replace(" (출처: https://www.law.go.kr/s0)", "").replace(" (출처: https://www.law.go.kr/s1)", "")
        self.assertEqual(self.failed(self.run_lint(t)), ["sources"])

    def test_h1_fail(self):
        self.assertEqual(self.failed(self.run_lint(self.good + "\n# 두번째 제목\n")), ["h1_once"])
        self.assertEqual(self.failed(self.run_lint(self.good.replace("# 지게차운전기능사 실기 순서\n\n## ", "## ", 1))), ["h1_once"])

    def test_missing_stage_exit_2(self):
        r = subprocess.run([sys.executable, SCRIPT, self.write("s.md", self.good)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)

    def test_comma_string_tags(self):
        t = self.good.replace(self.good.split("\n")[4], "tags: 가, 나, 다")
        res = self.run_lint(t)
        self.assertEqual(self.failed(res), [])
        self.assertEqual(res["stats"]["tags"], 3)

    def test_multiline_inline_tags(self):
        t = self.good.replace(self.good.split("\n")[4], "tags: [가,\n  나,\n  다]")
        res = self.run_lint(t)
        self.assertEqual(self.failed(res), [])
        self.assertEqual(res["stats"]["tags"], 3)

    def test_non_list_tags_fail(self):
        res = self.run_lint(self.good.replace(self.good.split("\n")[4], "tags: {a: b}"))
        self.assertEqual(self.failed(res), ["tags_count"])
        detail = next(c["detail"] for c in res["checks"] if c["id"] == "tags_count")
        self.assertEqual(detail, "리스트 형식 아님")

    def test_non_string_keyword_fail(self):
        res = self.run_lint(self.good.replace("keyword: 지게차 운전기능사", "keyword: [지게차, 운전기능사]"))
        self.assertEqual(self.failed(res), ["title_keyword"])

    def test_unclosed_frontmatter(self):
        res = self.run_lint(self.good.replace("---\n# 지게차", "# 지게차", 1))
        self.assertIn("frontmatter", self.failed(res))
        detail = next(c["detail"] for c in res["checks"] if c["id"] == "frontmatter")
        self.assertEqual(detail, "닫는 --- 없음")

    def test_bom_stripped(self):
        self.assertEqual(self.failed(self.run_lint("\ufeff" + self.good)), [])

    def test_unique_related_links(self):
        t = self.good.replace("pajuclark/2", "pajuclark/1")
        self.assertEqual(self.failed(self.run_lint(t)), ["related_links"])

    def test_decode_error_exit_2(self):
        p = os.path.join(self.root, "bin.md")
        with open(p, "wb") as f:
            f.write(b"\xff\xfe\x80\x81 bad")
        r = subprocess.run([sys.executable, SCRIPT, p, "--stage", "draft"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("UTF-8", r.stderr)

    def test_missing_knowledge_file_warning(self):
        with tempfile.TemporaryDirectory() as d:
            kd = os.path.join(d, "knowledge")
            os.makedirs(kd)
            with open(os.path.join(kd, "design-system.md"), "w", encoding="utf-8") as f:
                f.write(DESIGN)
            r = subprocess.run([sys.executable, SCRIPT, self.write("w.md", self.good), "--stage", "final",
                                "--knowledge", kd], capture_output=True, text=True)
            self.assertIn("academy-profile.md", r.stderr)
            self.assertNotIn("design-system.md", r.stderr)


if __name__ == "__main__":
    unittest.main()
