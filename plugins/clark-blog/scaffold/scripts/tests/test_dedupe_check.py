import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import dedupe_check  # noqa: E402

POSTS = [
    {"title": "9월 지게차운전기능사 시험일정｜필기·실기 원서접수 방법 (서울 의정부중장비학원)", "date": "2026-09-02"},
    {"title": "2025년 1월 지게차운전기능사 국비과정 주말반 개강 안내(재직자 수강 가능)", "date": "2025-01-10"},
    {"title": "내일배움카드로 국비교육 신청하는 방법(의정부,양주, 동두천 중장비운전학원)", "date": "2024-07-16"},
    {"title": "지게차 면허 갱신 서류 안내", "date": "2023-01-01"},
]


class DedupeTest(unittest.TestCase):
    def test_jaccard_duplicate(self):
        j, core, lab, title, _ = dedupe_check.judge("지게차 면허 갱신 서류", "갱신", POSTS)
        self.assertEqual(lab, "○")
        self.assertGreaterEqual(j, 0.5)
        self.assertIn("갱신", title)

    def test_core_token_duplicate(self):
        j, core, lab, title, _ = dedupe_check.judge("2025 시험 정보 총정리", "지게차운전기능사 시험일정", POSTS)
        self.assertLess(j, 0.5)
        self.assertGreaterEqual(core, 2)
        self.assertEqual(lab, "○")
        self.assertIn("시험일정", title)

    def test_partial_band(self):
        j, core, lab, title, _ = dedupe_check.judge("내일배움카드로 학원비부담 줄이는 방법", "내일배움카드", POSTS)
        self.assertEqual(lab, "△")
        self.assertTrue(0.25 <= j < 0.5)
        self.assertIn("내일배움카드", title)

    def test_no_overlap(self):
        self.assertEqual(dedupe_check.judge("건설기계조종사 안전교육 총정리", "건설기계조종사 안전교육", POSTS)[2], "×")

    def test_notice_marker_matches_same_marker_post(self):
        j, core, lab, title, date = dedupe_check.judge("경기북부 지게차학원｜10월 개강안내", "국비교육 일정", POSTS, notice=True)
        self.assertEqual(lab, "○")
        self.assertIn("개강", title)
        self.assertEqual(date, "2025-01-10")

    def test_notice_off_does_not_force_duplicate(self):
        self.assertNotEqual(dedupe_check.judge("경기북부 지게차학원｜10월 개강안내", "국비교육 일정", POSTS)[3], "")


if __name__ == "__main__":
    unittest.main()
