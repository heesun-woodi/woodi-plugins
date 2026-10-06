import os
import contextlib
import io
import re
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import gen_image  # noqa: E402

PLAN = """# 이미지 계획 — posts/001-test
| 슬롯 | 위치(소제목) | 목적 | 유형 | 프롬프트(ai) / 후보 파일(photo) | 캡션(alt) | 파일 | 검수 |
|---|---|---|---|---|---|---|---|
| 01 | 제목 아래(표지) | 표지 | ai | forklift on a cone course | 코스 주행 | images/01-cover.png | |
| 02 | ## 학원 소개 | 학원 CTA | photo | photos/a.jpg, photos/b.jpg | 실습장 | (게이트 3에서 확정) | |
| 03 | ## 시험 | 시험 | AI | examiner seen from behind | 시험 장면 | | |
"""

PATTERNS = os.path.join(HERE, "..", "..", "..", "skills", "blog-image-director", "references", "prompt-patterns.md")


class GenImagePlanTest(unittest.TestCase):
    def test_parse_splits_ai_and_photo_and_only_filter(self):
        idx, rows = gen_image.parse_plan(PLAN)
        self.assertEqual([r["slot"] for r in rows], ["01", "02", "03"])
        ai = gen_image.select_ai_rows(rows)
        self.assertEqual([r["slot"] for r in ai], ["01", "03"])
        self.assertEqual([gen_image.target_name(r) for r in ai], ["01-cover.png", "03-exam.png"])
        only = gen_image.select_ai_rows(rows, gen_image.parse_only("3"))
        self.assertEqual([r["slot"] for r in only], ["03"])
        with self.assertRaises(ValueError):
            gen_image.select_ai_rows(rows, gen_image.parse_only("02"))  # photo
        with self.assertRaises(ValueError):
            gen_image.select_ai_rows(rows, gen_image.parse_only("09"))  # 없음
        out = gen_image.rewrite_plan(PLAN, idx, {ai[1]["line"]: "images/03-exam.png"})
        self.assertIn("| 03 | ## 시험 | 시험 | AI | examiner seen from behind | 시험 장면 | images/03-exam.png | |", out)
        self.assertIn("(게이트 3에서 확정)", out)

    @unittest.skipUnless(os.path.isfile(PATTERNS), "플러그인 밖(작업 폴더)에서는 prompt-patterns.md가 없음")
    def test_prefix_suffix_match_prompt_patterns(self):
        with open(PATTERNS, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(re.search(r"- 접두: `([^`]+)`", text).group(1), gen_image.PROMPT_PREFIX)
        self.assertEqual(re.search(r"- 접미: `([^`]+)`", text).group(1), gen_image.PROMPT_SUFFIX)


    def test_parser_stops_at_blank_line_and_rejects_extra_cells(self):
        _, rows = gen_image.parse_plan(PLAN + "\n| 09 | x | 표지 | ai | p | c | | |\n")
        self.assertEqual(len(rows), 3)
        bad = PLAN.replace("| 03 | ## 시험 |", "| 03 | ## 시 | 험 |")
        with self.assertRaises(ValueError):
            gen_image.parse_plan(bad)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            _, rows = gen_image.parse_plan(PLAN.replace("| photo |", "| 사진 |"))
        self.assertIn("02", err.getvalue())
        self.assertEqual([r["slot"] for r in gen_image.select_ai_rows(rows)], ["01", "03"])


class EnvKeyTest(unittest.TestCase):
    def test_env_order_and_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            work = os.path.join(d, "work")
            plan_dir = os.path.join(work, "posts", "001", "images")
            os.makedirs(plan_dir)
            plan = os.path.join(plan_dir, "image-plan.md")
            # plan 바로 위 .env에는 키가 없음 → 계속 찾아 작업 폴더 .env를 써야 함
            with open(os.path.join(work, "posts", ".env"), "w") as f:
                f.write("OTHER=1\n")
            with open(os.path.join(work, ".env"), "w") as f:
                f.write("# c\nexport GEMINI_API_KEY='abc 123' # note\n")
            cwd = os.getcwd()
            try:
                os.chdir(d)  # cwd/.env 없음
                with mock.patch.dict(os.environ, {}, clear=True):
                    key, src = gen_image.find_api_key(plan)
                    self.assertEqual(key, "abc 123")
                    self.assertTrue(src.endswith(os.path.join("work", ".env")))
                    with open(os.path.join(d, ".env"), "w") as f:
                        f.write("GEMINI_API_KEY=xyz # inline\n")
                    self.assertEqual(gen_image.find_api_key(plan)[0], "xyz")  # cwd가 plan 상위보다 먼저
            finally:
                os.chdir(cwd)


class PersistTest(unittest.TestCase):
    def test_partial_success_persists_after_exception_on_slot2(self):
        fake_google = types.ModuleType("google")
        fake_genai = types.ModuleType("google.genai")
        fake_genai.Client = lambda api_key, http_options=None: object()
        fake_genai.types = types.SimpleNamespace(HttpOptions=lambda **kw: kw)
        fake_google.genai = fake_genai
        with tempfile.TemporaryDirectory() as d:
            img = os.path.join(d, "posts", "001", "images")
            os.makedirs(img)
            plan = os.path.join(img, "image-plan.md")
            with open(plan, "w", encoding="utf-8") as f:
                f.write(PLAN.replace("images/01-cover.png", ""))
            env = os.path.join(d, ".env")
            with open(env, "w") as f:
                f.write("GEMINI_API_KEY=k\n")
            calls = []

            def fake_gen(client, model, prompt):
                calls.append(prompt)
                if len(calls) == 2:
                    raise KeyboardInterrupt
                return b"png"

            def fake_save(data, out, width):
                with open(out, "wb") as f:
                    f.write(data)
                return "원본"

            with mock.patch.dict(sys.modules, {"google": fake_google, "google.genai": fake_genai}), \
                    mock.patch.object(gen_image, "generate_one", fake_gen), \
                    mock.patch.object(gen_image, "save_image", fake_save), \
                    contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    gen_image.main([plan, "--env", env])
            with open(plan, encoding="utf-8") as f:
                text = f.read()
            self.assertIn("| 01 | 제목 아래(표지) | 표지 | ai | forklift on a cone course | 코스 주행 | images/01-cover.png | |", text)
            self.assertNotIn("03-exam.png", text)
            self.assertTrue(os.path.isfile(os.path.join(img, "01-cover.png")))
            self.assertEqual([n for n in os.listdir(img) if n.endswith(".tmp")], [])


class QuotaTest(unittest.TestCase):
    def test_429_stops_remaining_slots_without_retry(self):
        class APIError(Exception):
            def __init__(self, code, message):
                super().__init__(message)
                self.code, self.message = code, message

        calls, seen_opts = [], {}

        class FakeClient:
            def __init__(self, api_key, http_options=None):
                seen_opts["http_options"] = http_options
                self.interactions = self

            def create(self, **kw):
                calls.append(kw)
                raise APIError(429, "RESOURCE_EXHAUSTED")

        fake_google = types.ModuleType("google")
        fake_genai = types.ModuleType("google.genai")
        fake_genai.Client = FakeClient
        fake_genai.types = types.SimpleNamespace(HttpOptions=lambda **kw: kw)
        fake_genai.errors = types.SimpleNamespace(APIError=APIError)
        fake_google.genai = fake_genai
        with tempfile.TemporaryDirectory() as d:
            img = os.path.join(d, "posts", "001", "images")
            os.makedirs(img)
            plan = os.path.join(img, "image-plan.md")
            with open(plan, "w", encoding="utf-8") as f:
                f.write(PLAN)
            env = os.path.join(d, ".env")
            with open(env, "w") as f:
                f.write("GEMINI_API_KEY=k\n")
            err = io.StringIO()
            with mock.patch.dict(sys.modules, {"google": fake_google, "google.genai": fake_genai}), \
                    mock.patch.object(gen_image.time, "sleep") as sleep, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                rc = gen_image.main([plan, "--env", env])
            self.assertEqual(rc, 1)
            self.assertEqual(len(calls), 1)          # 재시도 없음, 슬롯 03은 시도하지 않음
            sleep.assert_not_called()
            self.assertEqual(seen_opts["http_options"], {"timeout": gen_image.HTTP_TIMEOUT_MS})
            self.assertIn("결제(Billing)", err.getvalue())
            self.assertIn("01, 03", err.getvalue())
            with open(plan, encoding="utf-8") as f:
                self.assertEqual(f.read(), PLAN)     # 성공 슬롯이 없으면 image-plan.md 그대로


if __name__ == "__main__":
    unittest.main()
