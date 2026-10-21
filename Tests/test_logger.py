import io
import os
import sys
import tempfile
import unittest

from Scripts import logger


class TestTeeStream(unittest.TestCase):
    def setUp(self):
        self.terminal = io.StringIO()
        self.log_file = io.StringIO()
        self.tee = logger._TeeStream(self.terminal, self.log_file)

    def test_writes_to_both(self):
        self.tee.write("hello\n")
        self.assertEqual(self.terminal.getvalue(), "hello\n")
        self.assertEqual(self.log_file.getvalue(), "hello\n")

    def test_ansi_codes_are_stripped_from_the_log_only(self):
        self.tee.write("\x1b[1;36mWarning\x1b[0m: something\n")
        self.assertEqual(self.terminal.getvalue(), "\x1b[1;36mWarning\x1b[0m: something\n")
        self.assertEqual(self.log_file.getvalue(), "Warning: something\n")

    def test_window_size_hint_is_stripped(self):
        self.tee.write("\x1b[8;30;100t")
        self.assertEqual(self.log_file.getvalue(), "")

    def test_progress_carriage_returns_become_newlines_in_the_log(self):
        self.tee.write("50%\r75%\r100%\n")
        self.assertEqual(self.terminal.getvalue(), "50%\r75%\r100%\n")
        self.assertEqual(self.log_file.getvalue(), "50%\n75%\n100%\n")

    def test_non_string_payloads_do_not_crash(self):
        self.tee.write(42)
        self.assertEqual(self.log_file.getvalue(), "42")

    def test_encoding_follows_the_terminal(self):
        class Terminal:
            encoding = "cp936"

            def write(self, data):
                pass

            def flush(self):
                pass

        self.assertEqual(logger._TeeStream(Terminal(), self.log_file).encoding, "cp936")

    def test_missing_encoding_falls_back_to_utf8(self):
        class Terminal:
            encoding = None

            def write(self, data):
                pass

            def flush(self):
                pass

        self.assertEqual(logger._TeeStream(Terminal(), self.log_file).encoding, "utf-8")

    def test_closed_terminal_still_logs(self):
        class Broken:
            encoding = "utf-8"

            def write(self, data):
                raise ValueError("I/O operation on closed file")

            def flush(self):
                raise ValueError("I/O operation on closed file")

        tee = logger._TeeStream(Broken(), self.log_file)
        tee.write("kept\n")
        tee.flush()
        self.assertEqual(self.log_file.getvalue(), "kept\n")


class TestEnable(unittest.TestCase):
    def setUp(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr

    def tearDown(self):
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def test_enable_creates_a_log_and_tees(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = logger.enable(tmp)
            self.assertTrue(os.path.exists(path))
            self.assertTrue(path.endswith(".log"))
            print("captured line")
            sys.stdout.flush()
            with open(path, encoding="utf-8") as f:
                self.assertIn("captured line", f.read())

    def test_second_call_returns_the_same_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = logger.enable(tmp)
            second = logger.enable(tmp)
            self.assertEqual(first, second)
            self.assertEqual(len([n for n in os.listdir(tmp) if n.endswith(".log")]), 1)


class TestMakeConsoleSafe(unittest.TestCase):
    def test_reconfigures_both_streams(self):
        class Stream:
            def __init__(self):
                self.calls = []

            def reconfigure(self, **kwargs):
                self.calls.append(kwargs)

        out, err = Stream(), Stream()
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            logger.make_console_safe()
        finally:
            sys.stdout, sys.stderr = old_out, old_err

        self.assertEqual(out.calls, [{"errors": "replace"}])
        self.assertEqual(err.calls, [{"errors": "replace"}])

    def test_streams_without_reconfigure_are_skipped(self):
        old_out = sys.stdout
        sys.stdout = io.StringIO()  # StringIO has no reconfigure()
        try:
            logger.make_console_safe()
        finally:
            sys.stdout = old_out


if __name__ == "__main__":
    unittest.main()
