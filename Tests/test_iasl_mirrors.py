import sys
import unittest
from unittest import mock

sys.path.insert(0, ".")

from Scripts import dsdt, resource_fetcher


class TestGithubMirrors(unittest.TestCase):
    def setUp(self):
        self.fetcher = resource_fetcher.ResourceFetcher()

    def test_github_mirrors_only_for_github_urls(self):
        self.assertEqual(self.fetcher._get_github_mirrors("https://example.com/x.zip"), [])
        mirrors = self.fetcher._get_github_mirrors(
            "https://github.com/acpica/acpica/releases/download/20251212/iasl-win-20251212.zip"
        )
        self.assertTrue(mirrors)
        for mirror in mirrors:
            self.assertTrue(mirror.startswith("https://"))
            self.assertIn("acpica/acpica/releases/download", mirror)

    def test_reachable_proxies_come_first(self):
        mirrors = self.fetcher._get_github_mirrors("https://github.com/a/b/releases/download/v1/x.zip")
        self.assertTrue(mirrors[0].startswith("https://gh-proxy.com/"))
        self.assertTrue(mirrors[1].startswith("https://ghproxy.net/"))

    def test_raw_mirrors_are_built_from_jsdelivr(self):
        mirrors = self.fetcher._get_raw_mirrors(
            "https://raw.githubusercontent.com/corpnewt/linux_iasl/main/iasl.zip"
        )
        self.assertIn("https://cdn.jsdelivr.net/gh/corpnewt/linux_iasl@main/iasl.zip", mirrors)
        self.assertIn("https://fastly.jsdelivr.net/gh/corpnewt/linux_iasl@main/iasl.zip", mirrors)
        self.assertIn("https://gcore.jsdelivr.net/gh/corpnewt/linux_iasl@main/iasl.zip", mirrors)

    def test_raw_mirrors_empty_for_other_urls(self):
        self.assertEqual(self.fetcher._get_raw_mirrors("https://example.com/x"), [])


class TestIaslCandidates(unittest.TestCase):
    def _dsdt(self, releases):
        obj = dsdt.DSDT.__new__(dsdt.DSDT)
        obj.github = mock.Mock()
        obj.github.get_release_tags = mock.Mock(return_value=["r1", "r2"])
        obj.github.get_release_by_tag = mock.Mock(side_effect=lambda owner, repo, tag: releases[tag])
        return obj

    def test_candidates_collect_every_windows_artifact(self):
        releases = {
            "r1": {
                "body": "",
                "assets": [
                    {"url": "https://github.com/acpica/acpica/releases/download/r1/iasl-win-r1.zip"},
                    {"url": "https://github.com/acpica/acpica/releases/download/r1/iasl.exe"},
                ],
            },
            "r2": {
                "body": "",
                "assets": [
                    {"url": "https://github.com/acpica/acpica/releases/download/r2/iasl-win-r2.zip"},
                ],
            },
        }
        obj = self._dsdt(releases)
        candidates = obj.get_iasl_candidates()
        self.assertIn(
            "https://github.com/acpica/acpica/releases/download/r1/iasl-win-r1.zip", candidates
        )
        self.assertIn(
            "https://github.com/acpica/acpica/releases/download/r2/iasl-win-r2.zip", candidates
        )
        self.assertEqual(obj.get_latest_iasl(), candidates[0])

    def test_body_links_are_used(self):
        releases = {
            "r1": {
                "body": 'see "https://github.com/acpica/acpica/releases/download/r1/iasl-win-r1.zip"',
                "assets": [],
            },
            "r2": {"body": "", "assets": []},
        }
        obj = self._dsdt(releases)
        candidates = obj.get_iasl_candidates()
        self.assertEqual(
            candidates[0], "https://github.com/acpica/acpica/releases/download/r1/iasl-win-r1.zip"
        )


class TestIaslDownloadFailure(unittest.TestCase):
    def test_failed_download_raises_instead_of_extracting(self):
        obj = dsdt.DSDT.__new__(dsdt.DSDT)
        obj.u = mock.Mock()
        obj.fetcher = mock.Mock()
        obj.fetcher.download_and_save_file = mock.Mock(return_value=False)
        obj.fetcher._get_github_mirrors = mock.Mock(return_value=[])
        obj.fetcher._get_raw_mirrors = mock.Mock(return_value=[])
        with self.assertRaises(Exception):
            obj._download_and_extract("/tmp", "https://github.com/a/b/releases/download/v1/iasl-win-v1.zip")


if __name__ == "__main__":
    unittest.main()
