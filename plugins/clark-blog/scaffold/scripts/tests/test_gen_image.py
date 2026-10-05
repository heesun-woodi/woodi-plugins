import os
import re
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main()
