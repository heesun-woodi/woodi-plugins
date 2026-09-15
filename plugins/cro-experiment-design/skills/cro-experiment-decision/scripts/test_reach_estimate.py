#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reach_estimate.py 회귀 테스트.

실행: 이 폴더에서 `python3 -m unittest`
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import reach_estimate as re_mod  # noqa: E402  (경로 주입 이후 import)

# em 스킬의 statsig.py — 교차 검산용. 없으면 해당 테스트만 skip 한다.
STATSIG_PATH = (
    SCRIPT_DIR.parent.parent / "cro-experiment-monitoring" / "scripts" / "statsig.py"
)


def run_cli(*argv):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "reach_estimate.py"), *argv],
        capture_output=True,
        text=True,
    )
    return proc


class TestDaysToReach(unittest.TestCase):
    def test_ceiling(self):
        self.assertEqual(re_mod.days_to_reach(1411, 103), 14)

    def test_exact_division_no_extra_day(self):
        self.assertEqual(re_mod.days_to_reach(200, 100), 2)

    def test_reached_is_zero(self):
        self.assertEqual(re_mod.days_to_reach(0, 100), 0)
        self.assertEqual(re_mod.days_to_reach(-5, 100), 0)

    def test_zero_daily_is_none(self):
        self.assertIsNone(re_mod.days_to_reach(500, 0))

    def test_missing_daily_is_none(self):
        self.assertIsNone(re_mod.days_to_reach(500, None))


class TestGoldenReach(unittest.TestCase):
    """골든: 필요 1571 · 누적 160 · 일 103 · 기준일 2026-09-15."""

    def setUp(self):
        self.result = json.loads(
            run_cli(
                "--need-n", "1571",
                "--have", "160",
                "--daily", "103",
                "--today", "2026-09-15",
                "--launch", "2026-09-08",
                "--min-days", "16",
                "--format", "json",
            ).stdout
        )

    def test_remaining_n(self):
        self.assertEqual(self.result["군별"][0]["잔여_n"], 1411)

    def test_remaining_days(self):
        self.assertEqual(self.result["군별"][0]["잔여_일수"], 14)

    def test_reach_date(self):
        self.assertEqual(self.result["예상_도달일"], "2026-09-29")

    def test_min_observation_end(self):
        self.assertEqual(self.result["최소_관찰_종료일"], "2026-09-24")

    def test_proposed_end_is_max_of_two(self):
        self.assertEqual(self.result["연장_종료일_제안"], "2026-09-29")


class TestPlannedEndDelta(unittest.TestCase):
    def test_delta_days_and_wording(self):
        proc = run_cli(
            "--need-n", "1571",
            "--have", "160",
            "--daily", "103",
            "--today", "2026-09-15",
            "--launch", "2026-09-08",
            "--min-days", "16",
            "--planned-end", "2026-09-24",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("5일 늦음", proc.stdout)

    def test_no_cell_starts_with_equals_or_plus(self):
        proc = run_cli(
            "--need-n", "1571",
            "--have", "160", "140",
            "--daily", "103", "98",
            "--today", "2026-09-15",
            "--launch", "2026-09-08",
            "--min-days", "16",
            "--planned-end", "2026-09-24",
            "--project", "--control", "1600", "944", "--treatment", "1600", "990",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for line in proc.stdout.splitlines():
            if not line.startswith("|"):
                continue
            for cell in line.strip().strip("|").split("|"):
                cell = cell.strip()
                self.assertFalse(
                    cell.startswith("=") or cell.startswith("+"),
                    "셀 첫 글자에 = 또는 + 가 있다: {!r}".format(cell),
                )


class TestEdgeCases(unittest.TestCase):
    def test_reached_when_remaining_not_positive(self):
        proc = run_cli(
            "--need-n", "1571", "--have", "1600", "--daily", "103",
            "--today", "2026-09-15",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("도달", proc.stdout)

    def test_zero_daily_is_unknown(self):
        proc = run_cli(
            "--need-n", "1571", "--have", "160", "--daily", "0",
            "--today", "2026-09-15",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("확인 불가", proc.stdout)

    def test_missing_daily_is_unknown(self):
        result = json.loads(
            run_cli(
                "--need-n", "1571", "--have", "160",
                "--today", "2026-09-15", "--format", "json",
            ).stdout
        )
        self.assertIsNone(result["군별"][0]["잔여_일수"])
        self.assertIsNone(result["예상_도달일"])
        self.assertTrue(result["일_유입_확인_불가_군"])

    def test_latest_arm_drives_reach_date(self):
        result = json.loads(
            run_cli(
                "--need-n", "1571",
                "--have", "1400", "160",
                "--daily", "103",
                "--today", "2026-09-15", "--format", "json",
            ).stdout
        )
        # 느린 군(누적 160)이 전체 예상 도달일을 정한다.
        self.assertEqual(result["예상_도달일"], "2026-09-29")

    def test_arm_labels(self):
        result = json.loads(
            run_cli(
                "--need-n", "100", "--have", "10", "20", "30",
                "--daily", "5", "--today", "2026-09-15", "--format", "json",
            ).stdout
        )
        self.assertEqual(
            [r["군"] for r in result["군별"]], ["대조군", "실험군1", "실험군2"]
        )

    def test_daily_length_mismatch_fails(self):
        proc = run_cli(
            "--need-n", "100", "--have", "10", "20", "30",
            "--daily", "5", "6", "--today", "2026-09-15",
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_bad_date_fails(self):
        proc = run_cli("--need-n", "100", "--have", "10", "--today", "2026/09/15")
        self.assertNotEqual(proc.returncode, 0)

    def test_project_requires_arms(self):
        proc = run_cli("--need-n", "100", "--have", "10", "--project")
        self.assertNotEqual(proc.returncode, 0)


class TestProjection(unittest.TestCase):
    def test_scale_counts(self):
        self.assertEqual(re_mod.scale_counts(1600, 944, 1571), 927)
        self.assertEqual(re_mod.scale_counts(1600, 990, 1571), 972)

    def test_projected_statsig_about_90(self):
        result = json.loads(
            run_cli(
                "--need-n", "1571", "--have", "1571", "1571", "--daily", "100",
                "--today", "2026-09-15",
                "--project", "--control", "1600", "944", "--treatment", "1600", "990",
                "--format", "json",
            ).stdout
        )
        self.assertAlmostEqual(result["도달_시점_예상"]["stat_sig_pct"], 90.0, delta=1.0)

    def test_matches_statsig_py(self):
        """같은 1571 환산 건수로 statsig.py를 돌려 stat-sig를 대조한다 (±1.0%p)."""
        if not STATSIG_PATH.exists():
            self.skipTest("statsig.py 를 찾지 못했습니다: {}".format(STATSIG_PATH))
        sc = re_mod.scale_counts(1600, 944, 1571)
        st = re_mod.scale_counts(1600, 990, 1571)
        proc = subprocess.run(
            [
                sys.executable, str(STATSIG_PATH),
                "--control", "1571", str(sc),
                "--treatment", "1571", str(st),
                "--force-verdict",
                "--format", "json",
            ],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            self.skipTest("statsig.py 실행 실패: {}".format(proc.stderr.strip()[:200]))
        payload = json.loads(proc.stdout)
        expected = _find_statsig_pct(payload)
        self.assertIsNotNone(expected, "statsig.py JSON에서 stat-sig 값을 찾지 못했습니다")
        mine = json.loads(
            run_cli(
                "--need-n", "1571", "--have", "1571", "1571", "--daily", "100",
                "--today", "2026-09-15",
                "--project", "--control", "1600", "944", "--treatment", "1600", "990",
                "--format", "json",
            ).stdout
        )["도달_시점_예상"]["stat_sig_pct"]
        self.assertAlmostEqual(mine, expected, delta=1.0)

    def test_bonferroni_raises_threshold(self):
        result = json.loads(
            run_cli(
                "--need-n", "1571", "--have", "1571", "1571", "--daily", "100",
                "--today", "2026-09-15",
                "--project", "--control", "1600", "944", "--treatment", "1600", "990",
                "--bonferroni", "4", "--format", "json",
            ).stdout
        )
        self.assertAlmostEqual(result["도달_시점_예상"]["유의_임계_pct"], 98.75, places=4)
        self.assertFalse(result["도달_시점_예상"]["유의_여부"])


def _find_statsig_pct(node):
    """statsig.py JSON 어디에 있든 statsig_pct 를 찾아 온다."""
    if isinstance(node, dict):
        if "statsig_pct" in node and isinstance(node["statsig_pct"], (int, float)):
            return node["statsig_pct"]
        for value in node.values():
            found = _find_statsig_pct(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_statsig_pct(value)
            if found is not None:
                return found
    return None


class TestTwoProportionZ(unittest.TestCase):
    def test_no_difference_is_zero_z(self):
        stats = re_mod.two_proportion_z(1000, 500, 1000, 500)
        self.assertAlmostEqual(stats["z"], 0.0, places=10)
        self.assertAlmostEqual(stats["statsig_pct"], 0.0, places=6)

    def test_direction_sign(self):
        self.assertGreater(re_mod.two_proportion_z(1000, 400, 1000, 500)["z"], 0)
        self.assertLess(re_mod.two_proportion_z(1000, 500, 1000, 400)["z"], 0)

    def test_normal_cdf_center(self):
        self.assertAlmostEqual(re_mod.normal_cdf(0.0), 0.5, places=12)


class TestStdlibOnlyImports(unittest.TestCase):
    ALLOWED = {"argparse", "datetime", "json", "math", "sys", "typing"}

    def test_only_allowed_imports(self):
        source = (SCRIPT_DIR / "reach_estimate.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import "):
                mod = stripped[len("import "):].split()[0].split(".")[0].rstrip(",")
                self.assertIn(mod, self.ALLOWED, "허용되지 않은 import: {}".format(line))
            elif stripped.startswith("from "):
                mod = stripped[len("from "):].split()[0].split(".")[0]
                if mod == "__future__":
                    continue
                self.assertIn(mod, self.ALLOWED, "허용되지 않은 import: {}".format(line))

    def test_does_not_import_statsig(self):
        source = (SCRIPT_DIR / "reach_estimate.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                self.assertNotIn("statsig", stripped)


if __name__ == "__main__":
    unittest.main()
