"""Regression tests for lzhoang2801/OpCore-Simplify#511.

A download that drops halfway finishes without raising, so the archive is only
rejected later by zipfile, as "File is not a zip file".  The fetcher now asks a
validator about the file it just wrote and retries when it looks incomplete.
"""

import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scripts import utils
from Scripts.resource_fetcher import ResourceFetcher


def make_zip(path, payload=b"hello world", name="payload.txt"):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, payload)
    return path


class FakeResponse(object):
    """The small part of http.client.HTTPResponse the progress reader uses."""

    def __init__(self, body, status=200):
        self._buffer = io.BytesIO(body)
        self._status = status

    def getcode(self):
        return self._status

    def getheader(self, name, default=None):
        if name.lower() == "content-length":
            return str(len(self._buffer.getvalue()))
        return default

    def read(self, size=-1):
        return self._buffer.read(size)

    def close(self):
        self._buffer.close()


class FakeFetcher(object):
    """A ResourceFetcher whose transport replays a scripted list of bodies."""

    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.requests = []

    def __call__(self, url, timeout=None, extra_headers=None):
        self.requests.append((url, extra_headers))
        if not self.bodies:
            return None
        return FakeResponse(self.bodies.pop(0))


class ZipValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.utils = utils.Utils()

    def test_complete_archive_validates(self):
        self.assertTrue(self.utils.is_valid_zip(make_zip(os.path.join(self.directory, "ok.zip"))))

    def test_truncated_archive_is_rejected(self):
        path = make_zip(os.path.join(self.directory, "cut.zip"), payload=b"x" * 4096)
        with open(path, "rb") as handle:
            data = handle.read()

        truncated = os.path.join(self.directory, "truncated.zip")
        with open(truncated, "wb") as handle:
            handle.write(data[:len(data) // 2])

        self.assertFalse(self.utils.is_valid_zip(truncated))

    def test_html_error_page_is_rejected(self):
        path = os.path.join(self.directory, "login.zip")
        with open(path, "wb") as handle:
            handle.write(b"<!DOCTYPE html><html><body>404</body></html>")
        self.assertFalse(self.utils.is_valid_zip(path))

    def test_empty_but_valid_archive_passes(self):
        # A central-directory-only zip has no members, so testzip() has nothing
        # to complain about - the validation must not reject an empty archive.
        path = os.path.join(self.directory, "notes.zip")
        with open(path, "wb") as handle:
            handle.write(b"PK\x05\x06" + b"\x00" * 18)  # empty but valid zip
        self.assertTrue(self.utils.is_valid_zip(path))


class DownloadValidationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.source_zip = make_zip(os.path.join(self.directory, "source.zip"), payload=b"z" * 8192)

    def read_source(self):
        with open(self.source_zip, "rb") as handle:
            return handle.read()

    def fetcher_with(self, bodies):
        fetcher = ResourceFetcher()
        replay = FakeFetcher(bodies)
        fetcher._make_request = replay
        return fetcher, replay

    def test_truncated_download_is_retried_until_the_archive_validates(self):
        payload = self.read_source()
        destination = os.path.join(self.directory, "product.zip")
        fetcher, replay = self.fetcher_with([payload[:len(payload) // 2], payload])

        result = fetcher.download_and_save_file(
            "https://example.invalid/product.zip",
            destination,
            validate=utils.Utils().is_valid_zip,
        )

        self.assertTrue(result)
        self.assertTrue(utils.Utils().is_valid_zip(destination))
        self.assertEqual(len(replay.requests), 2)

    def test_endless_truncated_downloads_fail_instead_of_extracting(self):
        payload = self.read_source()
        destination = os.path.join(self.directory, "product.zip")
        fetcher, _ = self.fetcher_with([payload[:len(payload) // 2]] * 3)

        result = fetcher.download_and_save_file(
            "https://example.invalid/product.zip",
            destination,
            validate=utils.Utils().is_valid_zip,
        )

        self.assertFalse(result)
        self.assertFalse(os.path.exists(destination), "a rejected archive must not be left behind")

    def test_validator_is_optional(self):
        payload = self.read_source()
        destination = os.path.join(self.directory, "product.zip")
        fetcher, replay = self.fetcher_with([payload])

        self.assertTrue(fetcher.download_and_save_file("https://example.invalid/product.zip", destination))
        self.assertEqual(len(replay.requests), 1)


if __name__ == "__main__":
    unittest.main()
