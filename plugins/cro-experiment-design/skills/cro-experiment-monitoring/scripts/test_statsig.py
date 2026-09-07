#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""statsig.py 골든 테스트 — unittest만 사용.

검산 출처: DEC-018 승인 플랜의 「검증 1. 단위 테스트」 절.
숫자는 이 세션에서 사전 검산되었고, 허용 오차는 각 테스트에 그대로 반영했다.

주의: KB09 예시 2·3(p 0.07/0.09, 93%/96% 기재)은 원표 재계산과 불일치하여
오라클로 쓰지 않는다 — 예시 1((886,171)/(909,185), p 0.61·CI[-2.65,+4.73]·71%)만
정합성 확인용으로 사용한다.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import time
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import statsig  # noqa: E402  (경로 주입 이후 import)

PYTHON = sys.executable
STATSIG_PY = str(SCRIPT_DIR / "statsig.py")


def run_cli(args, timeout=10):
    proc = subprocess.run(
        [PYTHON, STATSIG_PY] + args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc


class TestNormalCdf(unittest.TestCase):
    def test_center(self):
        self.assertAlmostEqual(statsig.normal_cdf(0.0), 0.5, places=9)

    def test_monotonic(self):
        self.assertLess(statsig.normal_cdf(-1.0), statsig.normal_cdf(1.0))


class TestTwoProportionGolden(unittest.TestCase):
    """검증 1 골든 벡터 — 풀링 z / 미풀링 CI."""

    def test_vector_1(self):
        r = statsig.two_proportion_test(886, 171, 909, 185)
        self.assertAlmostEqual(r["diff_pp"], 1.05, delta=0.02)
        self.assertAlmostEqual(r["z"], 0.56, delta=0.02)
        self.assertAlmostEqual(r["p_two_sided"], 0.576, delta=0.01)
        self.assertAlmostEqual(r["ci_lo_pp"], -2.64, delta=0.05)
        self.assertAlmostEqual(r["ci_hi_pp"], 4.74, delta=0.05)

    def test_vector_2(self):
        r = statsig.two_proportion_test(1000, 180, 1000, 210)
        self.assertAlmostEqual(r["p_two_sided"], 0.090, delta=0.005)
        self.assertAlmostEqual(r["ci_lo_pp"], -0.47, delta=0.05)
        self.assertAlmostEqual(r["ci_hi_pp"], 6.47, delta=0.05)
        self.assertAlmostEqual(r["lift_rel_pct"], 16.67, delta=0.05)

    def test_vector_3(self):
        r = statsig.two_proportion_test(1200, 240, 1200, 264)
        self.assertAlmostEqual(r["p_two_sided"], 0.229, delta=0.005)
        self.assertAlmostEqual(r["ci_lo_pp"], -1.26, delta=0.05)
        self.assertAlmostEqual(r["ci_hi_pp"], 5.26, delta=0.05)


class TestGammq(unittest.TestCase):
    """df=1 카이제곱 상부 확률은 erfc(sqrt(x/2))와 1e-9 이내 일치해야 한다."""

    def test_identity_with_erfc(self):
        for chi2 in (0.02, 0.2, 1.0, 2.0, 4.0, 10.0, 20.0, 40.0):
            x = chi2 / 2.0
            got = statsig.gammq(0.5, x)
            want = math.erfc(math.sqrt(x))
            self.assertAlmostEqual(got, want, delta=1e-9)


class TestSrm(unittest.TestCase):
    def test_ok(self):
        chi2, df, p, flag = statsig.chi_square_srm([886, 909], [0.5, 0.5])
        self.assertAlmostEqual(chi2, 0.295, delta=0.01)
        self.assertAlmostEqual(p, 0.587, delta=0.01)
        self.assertEqual(df, 1)
        self.assertEqual(flag, "ok")

    def test_alarm(self):
        chi2, df, p, flag = statsig.chi_square_srm([5500, 4500], [0.5, 0.5])
        self.assertLess(p, 0.001)
        self.assertEqual(flag, "alarm")

    def test_three_arm_df2(self):
        chi2, df, p, flag = statsig.chi_square_srm([1000, 1000, 1000], [34, 33, 33])
        self.assertEqual(df, 2)
        self.assertEqual(flag, "ok")
        self.assertGreaterEqual(p, 0.01)

    def test_flag_boundaries(self):
        self.assertEqual(statsig.srm_flag_from_p(0.5), "ok")
        self.assertEqual(statsig.srm_flag_from_p(0.005), "warn")
        self.assertEqual(statsig.srm_flag_from_p(0.0001), "alarm")


class TestBayes(unittest.TestCase):
    VECTORS = [
        (886, 171, 909, 185, 0.712, 0.015),
        (1000, 180, 1000, 210, 0.954, 0.01),
        (1200, 240, 1200, 264, 0.884, 0.015),
    ]

    def test_mc(self):
        for nc, xc, nt, xt, expected, tol in self.VECTORS:
            got = statsig.bayes_prob_treatment_better_mc(nc, xc, nt, xt, seed=20260907, draws=200000)
            self.assertAlmostEqual(got, expected, delta=tol)

    def test_integrate_matches_mc_golden(self):
        for nc, xc, nt, xt, expected, _tol in self.VECTORS:
            got = statsig.bayes_prob_treatment_better_integrate(nc, xc, nt, xt)
            self.assertAlmostEqual(got, expected, delta=0.005)

    def test_mc_and_integrate_agree(self):
        for nc, xc, nt, xt, _expected, _tol in self.VECTORS:
            mc = statsig.bayes_prob_treatment_better_mc(nc, xc, nt, xt, seed=20260907, draws=200000)
            it = statsig.bayes_prob_treatment_better_integrate(nc, xc, nt, xt)
            self.assertAlmostEqual(mc, it, delta=0.005)


class TestMde(unittest.TestCase):
    def test_abs_not_met(self):
        # (886,171)/(909,185) diff=1.05%p=0.0105 < mde_abs 0.066
        met = statsig.compute_mde_met(diff_ratio=0.0105181, mde_abs=0.066, mde_rel=None, baseline=None)
        self.assertFalse(met)

    def test_abs_met(self):
        met = statsig.compute_mde_met(diff_ratio=0.08, mde_abs=0.066, mde_rel=None, baseline=None)
        self.assertTrue(met)

    def test_rel_met(self):
        met = statsig.compute_mde_met(diff_ratio=0.03, mde_abs=None, mde_rel=0.10, baseline=0.658)
        self.assertIsNotNone(met)

    def test_none_when_unspecified(self):
        met = statsig.compute_mde_met(diff_ratio=0.03, mde_abs=None, mde_rel=None, baseline=None)
        self.assertIsNone(met)


class TestVerdict(unittest.TestCase):
    def test_win(self):
        self.assertEqual(statsig.determine_verdict(100.0, 6.6, True, 95.0, 80.0), "WIN")
        self.assertEqual(statsig.determine_verdict(100.0, 6.6, None, 95.0, 80.0), "WIN")

    def test_lose(self):
        self.assertEqual(statsig.determine_verdict(100.0, -6.6, None, 95.0, 80.0), "LOSE")

    def test_inconclusive_mde_not_met(self):
        self.assertEqual(statsig.determine_verdict(96.0, 1.0, False, 95.0, 80.0), "INCONCLUSIVE")

    def test_continue_80(self):
        self.assertEqual(statsig.determine_verdict(85.0, 1.0, None, 95.0, 80.0), "CONTINUE_80")

    def test_inconclusive_low_statsig(self):
        self.assertEqual(statsig.determine_verdict(42.37, 1.05, None, 95.0, 80.0), "INCONCLUSIVE")


class TestGateLogic(unittest.TestCase):
    def test_gate_n_not_reached(self):
        reached, reason = statsig.evaluate_gate([886, 909], gate_n=1000, min_days=None, days_elapsed=None)
        self.assertFalse(reached)

    def test_gate_n_reached(self):
        reached, reason = statsig.evaluate_gate([886, 909], gate_n=800, min_days=None, days_elapsed=None)
        self.assertTrue(reached)

    def test_min_days_not_reached(self):
        import datetime

        launch = datetime.date(2026, 9, 1)
        today = datetime.date(2026, 9, 10)
        days_elapsed = (today - launch).days
        reached, reason = statsig.evaluate_gate([886, 909], gate_n=None, min_days=14, days_elapsed=days_elapsed)
        self.assertFalse(reached)


class TestBonferroni(unittest.TestCase):
    def test_alpha_effective_default(self):
        self.assertAlmostEqual(statsig.compute_alpha_effective(0.05, None), 0.05)

    def test_alpha_effective_with_k(self):
        self.assertAlmostEqual(statsig.compute_alpha_effective(0.05, 2), 0.025)

    def test_win_threshold_shifts_with_bonferroni(self):
        # alpha=0.05, K=2 -> alpha_effective=0.025 -> win 임계 97.5%
        alpha_eff = statsig.compute_alpha_effective(0.05, 2)
        win_threshold = (1 - alpha_eff) * 100
        self.assertAlmostEqual(win_threshold, 97.5)
        # statsig 96%는 K=2 하에서는 WIN이 아니라 CONTINUE_80 판정이어야 한다
        self.assertEqual(statsig.determine_verdict(96.0, 1.0, None, win_threshold, 80.0), "CONTINUE_80")
        # 보정 없으면 동일 96%가 WIN
        self.assertEqual(statsig.determine_verdict(96.0, 1.0, None, 95.0, 80.0), "WIN")


class TestCliJson(unittest.TestCase):
    def test_basic_json_keys(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIn("control", data)
        self.assertIn("treatments", data)
        self.assertIn("srm", data)
        self.assertIn("gate", data)
        t0 = data["treatments"][0]
        for key in (
            "label", "n", "x", "rate", "diff_pp", "lift_rel_pct", "z", "p_two_sided",
            "statsig_pct", "ci95_lo_pp", "ci95_hi_pp", "bayes_p_treatment_better",
            "mde_met", "verdict",
        ):
            self.assertIn(key, t0)

    def test_gate_health_masks_fields(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--gate-n", "1000",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["gate"]["mode"], "health")
        self.assertFalse(data["gate"]["gate_reached"])
        self.assertEqual(data["gate"]["suppressed_reason"], "gate")
        t0 = data["treatments"][0]
        for key in ("diff_pp", "lift_rel_pct", "z", "p_two_sided", "statsig_pct",
                    "ci95_lo_pp", "ci95_hi_pp", "bayes_p_treatment_better", "mde_met", "verdict"):
            self.assertIsNone(t0[key])

    def test_gate_verdict_mode(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--gate-n", "800",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["gate"]["mode"], "verdict")
        self.assertTrue(data["gate"]["gate_reached"])
        self.assertIsNone(data["gate"]["suppressed_reason"])
        self.assertIsNotNone(data["treatments"][0]["p_two_sided"])

    def test_min_days_gate_health(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--min-days", "14", "--launch", "2026-09-01", "--today", "2026-09-10",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["gate"]["mode"], "health")

    def test_srm_alarm_with_gate_reached_forces_design_fault(self):
        proc = run_cli([
            "--control", "5500", "1000",
            "--treatment", "4500", "900",
            "--gate-n", "100",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["srm"]["flag"], "alarm")
        self.assertEqual(data["gate"]["mode"], "verdict")
        self.assertEqual(data["gate"]["suppressed_reason"], "SRM")
        self.assertEqual(data["treatments"][0]["verdict"], "DESIGN_FAULT_SRM")
        self.assertIsNone(data["treatments"][0]["p_two_sided"])

    def test_srm_alarm_survives_force_verdict(self):
        proc = run_cli([
            "--control", "5500", "1000",
            "--treatment", "4500", "900",
            "--gate-n", "100000",
            "--force-verdict",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["srm"]["flag"], "alarm")
        self.assertEqual(data["gate"]["mode"], "verdict")
        self.assertEqual(data["treatments"][0]["verdict"], "DESIGN_FAULT_SRM")
        self.assertIn("피킹 게이트 강제 해제", proc.stderr)

    def test_force_verdict_warning_without_srm(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--gate-n", "100000",
            "--force-verdict",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["gate"]["mode"], "verdict")
        self.assertFalse(data["gate"]["gate_reached"])
        self.assertIn("피킹 게이트 강제 해제", proc.stderr)
        self.assertIsNotNone(data["treatments"][0]["p_two_sided"])

    def test_mde_abs_not_met(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--mde-abs", "0.066",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertFalse(data["treatments"][0]["mde_met"])

    def test_win_case_large_sample(self):
        proc = run_cli([
            "--control", "10000", "6580",
            "--treatment", "10000", "7240",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["treatments"][0]["verdict"], "WIN")

    def test_lose_case_large_sample(self):
        proc = run_cli([
            "--control", "10000", "7240",
            "--treatment", "10000", "6580",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["treatments"][0]["verdict"], "LOSE")

    def test_inconclusive_case(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--gate-n", "800",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertAlmostEqual(data["treatments"][0]["statsig_pct"], 42.37, delta=0.1)
        self.assertEqual(data["treatments"][0]["verdict"], "INCONCLUSIVE")

    def test_multi_treatment_and_ratio_srm(self):
        proc = run_cli([
            "--control", "1000", "180",
            "--treatment", "1000", "210",
            "--treatment", "1000", "200",
            "--ratio", "34", "33", "33",
            "--format", "json",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(len(data["treatments"]), 2)
        self.assertEqual(data["srm"]["flag"], "ok")


class TestMdRowNames(unittest.TestCase):
    REQUIRED_ROWS = [
        "절대 차이(%p)", "상대 리프트", "z", "p(양측)", "stat-sig(1−p)",
        "95% CI(미풀링)", "베이지안 P(실험군>대조군)", "MDE 달성", "다중비교 보정",
        "Amplitude 엔진 표시값(참고)", "SRM 카이제곱 p", "SRM 판정", "모드", "판정",
    ]

    def test_all_rows_present(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for row in self.REQUIRED_ROWS:
            self.assertIn(row, proc.stdout, f"누락된 행: {row}")

    def test_no_leading_plus_sign(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for line in proc.stdout.splitlines():
            cells = [c.strip() for c in line.split("|")]
            for cell in cells:
                self.assertFalse(cell.startswith("+"), f"'+'로 시작하는 셀: {cell!r}")

    def test_contract_boundary_comment_present(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(
            "<!-- 아래 10행 = 계약 M5b, 이어지는 4행 = M3b(SRM)·M4(모드)·M5c(판정)로 옮겨 적는다 -->",
            proc.stdout,
        )

    def test_amplitude_row_is_dash(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for line in proc.stdout.splitlines():
            if line.startswith("| Amplitude 엔진 표시값(참고) |"):
                cells = [c.strip() for c in line.split("|")]
                # cells = ['', 'Amplitude 엔진 표시값(참고)', '—', '']
                self.assertIn("—", cells)
                return
        self.fail("Amplitude 엔진 표시값(참고) 행을 찾지 못했다")

    def test_lift_and_statsig_values_carry_percent_sign(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for line in proc.stdout.splitlines():
            if line.startswith("| 상대 리프트 |") or line.startswith("| stat-sig(1−p) |"):
                self.assertIn("%", line)


class TestBonferroniMdLabel(unittest.TestCase):
    def test_no_bonferroni_label(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("해당 없음(2군)", proc.stdout)

    def test_bonferroni_label_with_k(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--bonferroni", "2",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Bonferroni α=0.0250(2비교)", proc.stdout)


class TestCliSmokeAndErrors(unittest.TestCase):
    def test_format_both_fast_and_ok(self):
        start = time.monotonic()
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "both",
        ])
        elapsed = time.monotonic() - start
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, 2.0)

    def test_missing_x_exits_2(self):
        proc = subprocess.run(
            [PYTHON, STATSIG_PY, "--control", "100"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 2)

    def test_ratio_count_mismatch_exits_2(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--ratio", "50", "30", "20",
        ])
        self.assertEqual(proc.returncode, 2)

    def test_mde_rel_without_baseline_exits_2(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--mde-rel", "0.1",
        ])
        self.assertEqual(proc.returncode, 2)

    def test_min_days_without_launch_today_exits_2(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--min-days", "14",
        ])
        self.assertEqual(proc.returncode, 2)


class TestArgValidation(unittest.TestCase):
    """[Critical] 인자 검증 — n>0, 0<=x<=n, sum(ratio)>0. 위반 시 exit 2 + 한국어 stderr."""

    def _assert_fails_ko(self, args):
        proc = run_cli(args)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertTrue(proc.stderr.strip(), "stderr가 비어 있습니다")
        self.assertTrue(
            any("가" <= ch <= "힣" for ch in proc.stderr),
            f"stderr에 한국어 메시지가 없습니다: {proc.stderr!r}",
        )
        self.assertNotIn("Traceback", proc.stderr)
        return proc

    def test_control_x_greater_than_n(self):
        self._assert_fails_ko([
            "--control", "100", "200",
            "--treatment", "100", "50",
        ])

    def test_control_n_negative(self):
        self._assert_fails_ko([
            "--control", "-10", "5",
            "--treatment", "100", "50",
        ])

    def test_control_x_negative(self):
        self._assert_fails_ko([
            "--control", "100", "-5",
            "--treatment", "100", "30",
        ])

    def test_control_n_zero(self):
        self._assert_fails_ko([
            "--control", "0", "0",
            "--treatment", "100", "30",
        ])

    def test_treatment_n_zero(self):
        self._assert_fails_ko([
            "--control", "100", "50",
            "--treatment", "0", "0",
        ])

    def test_ratio_sum_zero(self):
        self._assert_fails_ko([
            "--control", "100", "50",
            "--treatment", "100", "60",
            "--ratio", "0", "0",
        ])


class TestMultipleComparisonGate(unittest.TestCase):
    """[Major] 3군 이상에서 --bonferroni 미지정이면 판정을 마스킹한다 (계약 §3-8)."""

    def test_three_arm_without_bonferroni_masks_verdict(self):
        proc = run_cli([
            "--control", "1000", "180",
            "--treatment", "1000", "210",
            "--treatment", "1000", "200",
            "--ratio", "34", "33", "33",
            "--gate-n", "100",
            "--format", "both",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("다중비교 보정 | ⚠️확인필요", proc.stdout)
        json_part = proc.stdout[proc.stdout.rindex("\n\n{") + 2:]
        data = json.loads(json_part)
        for t in data["treatments"]:
            self.assertIsNone(t["verdict"])
            # 통계값은 게이트 통과 시 유지되어야 한다
            self.assertIsNotNone(t["p_two_sided"])
            self.assertIsNotNone(t["diff_pp"])
            self.assertIsNotNone(t["bayes_p_treatment_better"])

    def test_three_arm_with_bonferroni_computes_verdict(self):
        proc = run_cli([
            "--control", "1000", "180",
            "--treatment", "1000", "210",
            "--treatment", "1000", "200",
            "--ratio", "34", "33", "33",
            "--gate-n", "100",
            "--bonferroni", "2",
            "--format", "both",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Bonferroni α=0.0250(2비교)", proc.stdout)
        json_part = proc.stdout[proc.stdout.rindex("\n\n{") + 2:]
        data = json.loads(json_part)
        for t in data["treatments"]:
            self.assertIsNotNone(t["verdict"])

    def test_two_arm_no_warning(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("⚠️확인필요", proc.stdout)


class TestMdeMetLabel(unittest.TestCase):
    """[Major] 'MDE 달성' 값 도메인은 달성/미달 (계약 §3-8) — '미달성'이 아니다."""

    def test_fmt_bool_domain(self):
        self.assertEqual(statsig._fmt_bool(True), "달성")
        self.assertEqual(statsig._fmt_bool(False), "미달")
        self.assertNotEqual(statsig._fmt_bool(False), "미달성")

    def test_cli_md_shows_midal_not_midalseong(self):
        proc = run_cli([
            "--control", "886", "171",
            "--treatment", "909", "185",
            "--mde-abs", "0.066",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for line in proc.stdout.splitlines():
            if line.startswith("| MDE 달성 |"):
                self.assertIn("미달", line)
                self.assertNotIn("미달성", line)
                return
        self.fail("MDE 달성 행을 찾지 못했다")


class TestTreatmentRequired(unittest.TestCase):
    """[Minor] --treatment 미지정 시 한국어 오류 메시지로 exit 2."""

    def test_missing_treatment_korean_message(self):
        proc = run_cli(["--control", "100", "50"])
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("--treatment", proc.stderr)
        self.assertTrue(
            any("가" <= ch <= "힣" for ch in proc.stderr),
            f"stderr에 한국어 메시지가 없습니다: {proc.stderr!r}",
        )
        self.assertNotIn("Traceback", proc.stderr)


class TestCoverageGaps(unittest.TestCase):
    """[Minor] 커버리지 갭 — diff_pp==0 경계 / 3군 md 헤더 / bayes-method integrate 성능."""

    def test_diff_zero_boundary_inconclusive(self):
        self.assertEqual(
            statsig.determine_verdict(50.0, 0.0, None, 95.0, 80.0), "INCONCLUSIVE"
        )

    def test_three_arm_md_header_has_two_columns(self):
        proc = run_cli([
            "--control", "1000", "180",
            "--treatment", "1000", "210",
            "--treatment", "1000", "200",
            "--ratio", "34", "33", "33",
            "--format", "md",
        ])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("| 항목 | 실험군1 | 실험군2 |", proc.stdout)

    def test_bayes_integrate_large_sample_under_3s(self):
        start = time.monotonic()
        got = statsig.bayes_prob_treatment_better_integrate(50000, 10000, 50000, 10500)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 3.0, f"integrate가 {elapsed:.2f}s 걸렸습니다 (한도 3s)")
        self.assertGreaterEqual(got, 0.0)
        self.assertLessEqual(got, 1.0)


class TestOutFile(unittest.TestCase):
    def test_out_writes_json_file(self, tmp_path=SCRIPT_DIR / "_test_out.json"):
        try:
            proc = run_cli([
                "--control", "886", "171",
                "--treatment", "909", "185",
                "--format", "md",
                "--out", str(tmp_path),
            ])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(tmp_path.exists())
            data = json.loads(tmp_path.read_text(encoding="utf-8"))
            self.assertIn("control", data)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestStdlibOnlyImports(unittest.TestCase):
    ALLOWED = {"argparse", "math", "json", "random", "datetime", "sys", "dataclasses", "typing"}

    def test_only_allowed_imports(self):
        source = (SCRIPT_DIR / "statsig.py").read_text(encoding="utf-8")
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import "):
                mod = stripped[len("import "):].split()[0].split(".")[0].rstrip(",")
                self.assertIn(mod, self.ALLOWED, f"허용되지 않은 import: {line}")
            elif stripped.startswith("from "):
                mod = stripped[len("from "):].split()[0].split(".")[0]
                if mod == "__future__":
                    continue
                self.assertIn(mod, self.ALLOWED, f"허용되지 않은 import: {line}")


if __name__ == "__main__":
    unittest.main()
