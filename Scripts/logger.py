"""Duplicate everything the program prints into a log file.

The program is normally started by double-clicking OpCore-Simplify.bat (or
.command), so the console output disappears when the window closes.  Enabling
this module at import time keeps a copy on disk while the terminal still gets
the live, coloured output.

The log file is plain text: ANSI colour codes are stripped and the carriage
returns the progress bar uses become newlines, so the result can be read in any
editor or pasted into a bug report.
"""

import atexit
import datetime
import os
import re
import shutil
import sys

# Colour/escape sequences the program uses for its boxes, colours and the
# window-size hint.  \x1b[8;30;100t and \x1b[1;36m both match.
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

_LOG_DIRECTORY = "logs"
_LATEST_NAME = "latest.log"


class _TeeStream:
    """A stream that writes to the terminal and to a log file."""

    def __init__(self, terminal, log_file):
        self._terminal = terminal
        self._log_file = log_file

    # -- stream protocol ---------------------------------------------------
    @property
    def encoding(self):
        # resource_fetcher asks for this to pick block characters.
        return getattr(self._terminal, "encoding", None) or "utf-8"

    @property
    def errors(self):
        return getattr(self._terminal, "errors", None) or "replace"

    def isatty(self):
        isatty = getattr(self._terminal, "isatty", None)
        return bool(isatty()) if callable(isatty) else False

    def fileno(self):
        return self._terminal.fileno()

    def writable(self):
        return True

    def readable(self):
        return False

    def seekable(self):
        return False

    def write(self, data):
        if not isinstance(data, str):
            data = str(data)

        try:
            self._terminal.write(data)
        except (OSError, ValueError, UnicodeEncodeError):
            # A closed or unencodable console must not lose the log line.
            pass

        try:
            self._log_file.write(_ANSI_ESCAPE.sub("", data).replace("\r", "\n"))
        except (OSError, ValueError):
            pass

        return len(data)

    def flush(self):
        for stream in (self._terminal, self._log_file):
            try:
                stream.flush()
            except (OSError, ValueError):
                pass


def _log_path(directory):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(directory, "OpCore-Simplify-{}.log".format(stamp))


def make_console_safe():
    """Stop an unencodable glyph from killing the program.

    A Chinese Windows console (cp936) cannot encode a bullet, an English one
    (cp437) cannot encode the box drawing either.  With errors="replace" such a
    character degrades to "?" instead of raising UnicodeEncodeError from deep
    inside a print().  The log file still receives the original text.
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(errors="replace")
        except (OSError, ValueError):
            pass


def enable(log_directory=None):
    """Mirror stdout/stderr into a log file and return its path.

    Calling this twice is harmless: the second call does nothing and returns
    the path of the log that is already open.
    """
    current = getattr(sys.stdout, "_opcore_log_path", None)
    if current:
        return current

    make_console_safe()

    if not log_directory:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_directory = os.path.join(root, _LOG_DIRECTORY)

    os.makedirs(log_directory, exist_ok=True)
    path = _log_path(log_directory)
    log_file = open(path, "w", encoding="utf-8", errors="replace")

    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = _TeeStream(original_stdout, log_file)
    sys.stderr = _TeeStream(original_stderr, log_file)
    # Lets a second call (or a test) find the active log without a global.
    sys.stdout._opcore_log_path = path

    def _close():
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, _TeeStream):
                stream.flush()
        try:
            log_file.close()
        except (OSError, ValueError):
            pass
        # Keep a stable name for "send me the log" without losing history.
        try:
            shutil.copyfile(path, os.path.join(log_directory, _LATEST_NAME))
        except OSError:
            pass

    atexit.register(_close)
    return path
