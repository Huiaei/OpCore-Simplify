import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Scripts import github
from Scripts import resource_fetcher


class ApiFallbackTest(unittest.TestCase):
    def make_github(self, api_payload=None, html=""):
        g = github.Github()

        def fake_fetch(url, content_type=None, mirrors=None):
            if url.startswith("https://api.github.com/"):
                return api_payload
            return html

        g.fetcher.fetch_and_parse_content = fake_fetch
        return g

    def test_commits_fall_back_to_api(self):
        payload = [{
            "sha": "abc123",
            "commit": {
                "message": "Fix things\n\nmore",
                "author": {"name": "Ada", "date": "2026-10-20T10:00:00Z"},
                "committer": {"name": "Ada", "date": "2026-10-20T10:05:00Z"},
            },
        }]
        g = self.make_github(api_payload=payload)
        commits = g.get_commits("lzhoang2801", "OpCore-Simplify")

        self.assertEqual(commits["commitGroups"][0]["commits"][0]["oid"], "abc123")
        self.assertEqual(commits["currentCommit"]["oid"], "abc123")
        self.assertEqual(commits["commitGroups"][0]["commits"][0]["message"], "Fix things")
        self.assertEqual(commits["commitGroups"][0]["commits"][0]["committedDate"], "2026-10-20")

    def test_commits_api_failure_raises(self):
        g = self.make_github(api_payload=[])
        with self.assertRaises(ValueError):
            g.get_commits("lzhoang2801", "OpCore-Simplify")

    def test_latest_release_falls_back_to_api(self):
        payload = [{
            "tag_name": "2.7.2",
            "body": "notes",
            "assets": [{
                "id": 42,
                "name": "WhateverGreen-1.7.1-RELEASE.zip",
                "browser_download_url": "https://github.com/acidanthera/WhateverGreen/releases/download/1.7.1/WhateverGreen-1.7.1-RELEASE.zip",
                "digest": "sha256:" + "ab" * 32,
            }],
        }]
        g = self.make_github(api_payload=payload)
        release = g.get_latest_release("acidanthera", "WhateverGreen")

        self.assertEqual(release["tag"], "2.7.2")
        asset = release["assets"][0]
        self.assertEqual(asset["product_name"], "WhateverGreen")
        self.assertEqual(asset["id"], 42)
        self.assertEqual(asset["sha256"], "ab" * 32)

    def test_release_tags_fall_back_to_api(self):
        payload = [{"tag_name": "20260930"}, {"tag_name": "20260408"}]
        g = self.make_github(api_payload=payload)
        self.assertEqual(g.get_release_tags("acpica", "acpica"), ["20260930", "20260408"])

    def test_release_by_tag_falls_back_to_api(self):
        payload = {"tag_name": "2.7.2", "body": "", "assets": []}
        g = self.make_github(api_payload=payload)
        release = g.get_release_by_tag("acidanthera", "BrcmPatchRAM", "2.7.2")
        self.assertEqual(release["tag"], "2.7.2")

    def test_api_mirrors_are_used(self):
        g = github.Github()
        seen = {}

        def fake_fetch(url, content_type=None, mirrors=None):
            seen["url"] = url
            seen["mirrors"] = mirrors
            return []

        g.fetcher.fetch_and_parse_content = fake_fetch
        with self.assertRaises(ValueError):
            g.get_latest_commit_sha("lzhoang2801", "OpCore-Simplify")

        self.assertIn("https://gh-proxy.com/https://api.github.com/", seen["mirrors"][0])
        self.assertTrue(seen["mirrors"])


class MirrorHelperTest(unittest.TestCase):
    def setUp(self):
        self.fetcher = resource_fetcher.ResourceFetcher()

    def test_all_mirrors_combines_both_families(self):
        url = "https://raw.githubusercontent.com/acidanthera/MaciASL/master/Dist/iasl-stable"
        mirrors = self.fetcher._get_all_mirrors(url)

        self.assertTrue(any("jsdelivr.net" in m for m in mirrors))
        self.assertTrue(any("gh-proxy.com" in m for m in mirrors))

    def test_github_mirrors_are_prefixes(self):
        url = "https://github.com/acidanthera/WhateverGreen/releases/download/1.7.1/WhateverGreen-1.7.1-RELEASE.zip"
        mirrors = self.fetcher._get_github_mirrors(url)

        self.assertEqual(len(mirrors), 4)
        for mirror in mirrors:
            self.assertTrue(mirror.endswith(url))

    def test_non_github_url_has_no_github_mirrors(self):
        self.assertEqual(self.fetcher._get_github_mirrors("https://example.com/a.zip"), [])


if __name__ == "__main__":
    unittest.main()
