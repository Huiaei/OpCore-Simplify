import io
import re
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scripts import utils


class EncodingStdout:
    """Stand-in for a console that encodes writes with the given codec."""

    def __init__(self, encoding):
        self._codec = encoding
        # Real consoles expose this and the program asks for it.
        self.encoding = encoding
        self._buffer = io.StringIO()

    def write(self, s):
        s.encode(self._codec)
        return self._buffer.write(s)

    def flush(self):
        pass

    def getvalue(self):
        return self._buffer.getvalue()


def render_head(stdout_encoding):
    u = utils.Utils.__new__(utils.Utils)
    u.script_name = "OpCore Simplify"
    buf = EncodingStdout(stdout_encoding)
    old_stdout, old_system = sys.stdout, os.system
    sys.stdout, os.system = buf, lambda *a, **k: 0
    try:
        u.head("Check for Updates", resize=False)
    finally:
        sys.stdout, os.system = old_stdout, old_system
    return buf.getvalue()


def render_progress(stdout_encoding, done=False):
    u = utils.Utils.__new__(utils.Utils)
    u.script_name = "OpCore Simplify"
    buf = EncodingStdout(stdout_encoding)
    old_stdout, old_system = sys.stdout, os.system
    sys.stdout, os.system = buf, lambda *a, **k: 0
    try:
        u.progress_bar("Building OpenCore EFI", ["copy base", "apply patches"], 1, done=done)
    finally:
        sys.stdout, os.system = old_stdout, old_system
    return buf.getvalue()


def safe_glyph_under(stdout_encoding):
    u = utils.Utils.__new__(utils.Utils)
    buf = EncodingStdout(stdout_encoding)
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        return u.safe_glyph("\u2713", "+")
    finally:
        sys.stdout = old_stdout


class ConsoleFallbackTest(unittest.TestCase):
    def test_cp1252_falls_back_to_ascii_without_error(self):
        out = render_head("cp1252")
        lines = out.splitlines()
        self.assertEqual(len(lines), 3)
        self.assertTrue(all(len(line) == 68 for line in lines))
        self.assertTrue(lines[0].startswith("+") and lines[0].endswith("+"))
        self.assertIn("Check for Updates", lines[1])
        out.encode("cp1252")

    def test_utf8_keeps_box_drawing(self):
        out = render_head("utf-8")
        self.assertIn("╔", out)
        self.assertIn("Check for Updates", out)


    def test_progress_bar_falls_back_on_cp1252(self):
        out = render_progress("cp1252")
        plain = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", out)
        self.assertIn("[+] copy base", plain)
        self.assertNotIn("\u2713", plain)
        out.encode("cp1252")

    def test_progress_bar_keeps_the_tick_on_utf8(self):
        self.assertIn("\u2713", render_progress("utf-8"))

    def test_safe_glyph_falls_back_on_gbk(self):
        # cp936 has the box drawing but not the bullet.
        self.assertEqual(safe_glyph_under("gbk"), "+")
        self.assertEqual(safe_glyph_under("cp437"), "+")

    def test_safe_glyph_keeps_the_glyph_on_utf8(self):
        self.assertEqual(safe_glyph_under("utf-8"), "\u2713")

    def test_cp936_has_the_box_drawing_but_neither_glyph(self):
        # A Chinese Windows console renders the header box fine (U+2550 is in
        # cp936) yet cannot encode U+2022 or U+2713 - which is exactly how the
        # user's build died with a traceback-less "An Error Occurred".
        u = utils.Utils.__new__(utils.Utils)
        old_stdout = sys.stdout
        sys.stdout = EncodingStdout("gbk")
        try:
            self.assertEqual(u.safe_glyph("\u2022", "-"), "-")
            self.assertEqual(u.safe_glyph("\u2713", "+"), "+")
            self.assertEqual(u.safe_glyph("\u2550", "-"), "\u2550")
        finally:
            sys.stdout = old_stdout

if __name__ == "__main__":
    unittest.main()
