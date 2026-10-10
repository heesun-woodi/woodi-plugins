import contextlib
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from PIL import Image
except ImportError:
    Image = None
import make_cover


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = make_cover.main(argv)
    return code, out.getvalue(), err.getvalue()


@unittest.skipIf(Image is None, "Pillow 없음")
class MakeCoverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bg = os.path.join(self.tmp.name, "bg.png")
        Image.new("RGB", (1200, 800), (120, 140, 90)).save(self.bg)
        self.out = os.path.join(self.tmp.name, "images", "00-cover.png")
        if not make_cover.find_fonts():
            self.skipTest("한글 폰트 없음")

    def test_creates_square_rgb(self):
        code, _, err = run(["--bg", self.bg, "--title", "지게차 면허 갱신|주기와 준비물", "--sub", "의정부 중장비학원", "--out", self.out])
        self.assertEqual(code, 0, err)
        with Image.open(self.out) as im:
            self.assertEqual(im.size, (1000, 1000))
            self.assertEqual(im.mode, "RGB")

    def test_dry_run_lists_lines_and_writes_nothing(self):
        code, out, _ = run(["--bg", self.bg, "--title", "지게차 면허 갱신|주기와 준비물", "--out", self.out, "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("지게차 면허 갱신", out)
        self.assertIn("주기와 준비물", out)
        self.assertIn("px", out)
        self.assertFalse(os.path.exists(self.out))

    def test_long_line_wraps(self):
        title = "지게차 운전기능사 면허 갱신 주기와 준비물 서류 총정리 안내"
        code, out, _ = run(["--bg", self.bg, "--title", title, "--out", self.out, "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("줄 ", out)
        n = int(out.split("줄 ")[1].split("개")[0])
        self.assertGreaterEqual(n, 2)

    def test_no_font_exits_2(self):
        empty = os.path.join(self.tmp.name, "empty")
        os.makedirs(empty)
        code, _, err = run(["--bg", self.bg, "--title", "제목", "--out", self.out, "--font-dir", empty, "--no-system-fonts"])
        self.assertEqual(code, 2)
        self.assertIn("한글 폰트 없음", err)
        self.assertFalse(os.path.exists(self.out))

    def test_missing_bg_exits_2(self):
        code, _, err = run(["--bg", os.path.join(self.tmp.name, "nope.png"), "--title", "제목", "--out", self.out])
        self.assertEqual(code, 2)
        self.assertIn("배경", err)



class FontCandidatesTest(unittest.TestCase):
    """글꼴 탐색 순서(계약 B) — 실제 글꼴 없이 후보 목록·선택만 본다(Pillow 불필요)."""

    def test_order_with_windows_env(self):
        env = {"LOCALAPPDATA": os.path.join("L"), "WINDIR": os.path.join("W")}
        title, sub = make_cover.font_candidates("FD", True, env)
        lw = os.path.join("L", "Microsoft", "Windows", "Fonts")
        wf = os.path.join("W", "Fonts")
        self.assertEqual([p for p, _ in title], [
            os.path.join("FD", "Pretendard-ExtraBold.otf"),
            os.path.join(make_cover.USER_FONT_DIR, "Pretendard-ExtraBold.otf"),
            os.path.join(lw, "Pretendard-ExtraBold.otf"),
            os.path.join(wf, "Pretendard-ExtraBold.otf"),
            make_cover.APPLE_TTC,
            os.path.join(wf, "malgunbd.ttf")])
        self.assertEqual([p for p, _ in sub][-1], os.path.join(wf, "malgun.ttf"))
        self.assertEqual([p for p, _ in sub][2], os.path.join(lw, "Pretendard-SemiBold.otf"))

    def test_missing_env_skips_windows(self):
        title, sub = make_cover.font_candidates(None, True, {})
        self.assertEqual([p for p, _ in title], [os.path.join(make_cover.USER_FONT_DIR, "Pretendard-ExtraBold.otf"),
                                                 make_cover.APPLE_TTC])
        self.assertEqual(len(sub), 2)

    def test_no_system_fonts_only_font_dir(self):
        env = {"LOCALAPPDATA": "L", "WINDIR": "W"}
        title, sub = make_cover.font_candidates("FD", False, env)
        self.assertEqual(title, [(os.path.join("FD", "Pretendard-ExtraBold.otf"), 0)])
        self.assertEqual(sub, [(os.path.join("FD", "Pretendard-SemiBold.otf"), 0)])
        self.assertEqual(make_cover.font_candidates(None, False, env), ([], []))

    def test_find_fonts_windows_fallbacks(self):
        with tempfile.TemporaryDirectory() as t, \
                mock.patch.object(make_cover, "USER_FONT_DIR", os.path.join(t, "nope")), \
                mock.patch.object(make_cover, "APPLE_TTC", os.path.join(t, "nope.ttc")):
            local, win = os.path.join(t, "local"), os.path.join(t, "win")
            env = {"LOCALAPPDATA": local, "WINDIR": win}
            self.assertIsNone(make_cover.find_fonts(env=env))
            os.makedirs(os.path.join(win, "Fonts"))
            for n in ("malgunbd.ttf", "malgun.ttf"):
                open(os.path.join(win, "Fonts", n), "wb").close()
            self.assertEqual(make_cover.find_fonts(env=env), ((os.path.join(win, "Fonts", "malgunbd.ttf"), 0),
                                                              (os.path.join(win, "Fonts", "malgun.ttf"), 0)))
            self.assertIsNone(make_cover.find_fonts(env=env, system=False))
            ud = os.path.join(local, "Microsoft", "Windows", "Fonts")
            os.makedirs(ud)
            open(os.path.join(ud, "Pretendard-ExtraBold.otf"), "wb").close()
            title, sub = make_cover.find_fonts(env=env)
            self.assertEqual(title, (os.path.join(ud, "Pretendard-ExtraBold.otf"), 0))   # 사용자 글꼴 Pretendard 우선
            self.assertEqual(sub, (os.path.join(win, "Fonts", "malgun.ttf"), 0))

    def test_no_font_message_mentions_windows(self):
        self.assertIn("한글 폰트 없음", make_cover.NO_FONT_MSG)
        self.assertIn("malgunbd.ttf", make_cover.NO_FONT_MSG)

if __name__ == "__main__":
    unittest.main()
