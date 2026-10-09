import contextlib
import io
import os
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
