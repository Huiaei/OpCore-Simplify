import os
import socket
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from Scripts import resource_fetcher


class FakeResponse:
    """Minimal stand-in for the object urlopen() returns."""

    def __init__(self, payload, status=200, fail_after=None):
        self.payload = payload
        self.status = status
        self.fail_after = fail_after
        self.offset = 0
        self.closed = False

    def getcode(self):
        return self.status

    def getheader(self, name):
        if name.lower() == "content-length":
            return str(len(self.payload))
        return None

    def info(self):
        return {"Content-Length": str(len(self.payload))}

    def read(self, size=-1):
        if self.fail_after is not None and self.offset >= self.fail_after:
            raise socket.timeout("The read operation timed out")
        if size is None or size < 0:
            end = len(self.payload)
        else:
            end = min(self.offset + size, len(self.payload))
        if self.fail_after is not None:
            end = min(end, self.fail_after)
        chunk = self.payload[self.offset:end]
        self.offset = end
        return chunk

    def close(self):
        self.closed = True


class DownloadResumeTests(unittest.TestCase):
    def setUp(self):
        self.fetcher = resource_fetcher.ResourceFetcher()
        self.temp_dir = tempfile.mkdtemp()
        self.destination = os.path.join(self.temp_dir, "payload.zip")
        self.payload = bytes(range(256)) * 40  # 10 KB

    def tearDown(self):
        for name in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, name))
        os.rmdir(self.temp_dir)

    def _install(self, responses, requests):
        def fake_make_request(url, timeout=10, extra_headers=None):
            requests.append(dict(extra_headers or {}))
            if not responses:
                return None
            return responses.pop(0)

        self.fetcher._make_request = fake_make_request

    def test_stalled_download_resumes_with_range_header(self):
        requests = []
        self._install(
            [
                FakeResponse(self.payload[:4000], status=200, fail_after=4000),
                FakeResponse(self.payload[4000:], status=206),
            ],
            requests,
        )

        self.assertTrue(self.fetcher._download_with_retries("https://example.com/payload.zip", self.destination))

        with open(self.destination, "rb") as f:
            self.assertEqual(f.read(), self.payload)
        self.assertEqual(requests[0], {})
        self.assertEqual(requests[1].get("Range"), "bytes=4000-")

    def test_server_ignoring_range_restarts_from_zero(self):
        requests = []
        self._install(
            [
                FakeResponse(self.payload[:1000], status=200, fail_after=1000),
                # 200 instead of 206: the partial file must be truncated, not appended to
                FakeResponse(self.payload, status=200),
            ],
            requests,
        )

        self.assertTrue(self.fetcher._download_with_retries("https://example.com/payload.zip", self.destination))

        with open(self.destination, "rb") as f:
            self.assertEqual(f.read(), self.payload)

    def test_interrupted_download_does_not_propagate(self):
        requests = []
        self._install(
            [
                FakeResponse(self.payload[:512], status=200, fail_after=512),
                FakeResponse(self.payload[512:], status=206),
            ],
            requests,
        )

        # A socket timeout used to escape the retry loop and kill the whole build
        self.assertTrue(self.fetcher._download_with_retries("https://example.com/payload.zip", self.destination))

    def test_checksum_mismatch_retries_and_gives_up_cleanly(self):
        requests = []
        self._install(
            [
                FakeResponse(b"wrong" * 10, status=200),
                FakeResponse(b"wrong" * 10, status=200),
                FakeResponse(b"wrong" * 10, status=200),
            ],
            requests,
        )

        result = self.fetcher._download_with_retries(
            "https://example.com/payload.zip", self.destination, sha256_hash="0" * 64
        )

        self.assertFalse(result)
        self.assertEqual(len(requests), resource_fetcher.MAX_ATTEMPTS)

    def test_all_urls_failing_removes_partial_file(self):
        requests = []
        self._install([FakeResponse(b"partial", status=200, fail_after=7)], requests)

        def fake_make_request(url, timeout=10, extra_headers=None):
            requests.append(dict(extra_headers or {}))
            return FakeResponse(b"partial", status=200, fail_after=7)

        self.fetcher._make_request = fake_make_request

        result = self.fetcher.download_and_save_file(
            "https://example.com/payload.zip", self.destination, mirrors=["https://mirror.example.com/payload.zip"]
        )

        self.assertFalse(result)
        self.assertFalse(os.path.exists(self.destination))

    def test_download_timeout_is_longer_than_api_timeout(self):
        self.assertGreater(self.fetcher.download_timeout, 10)


if __name__ == "__main__":
    unittest.main()
