from Scripts import resource_fetcher
from Scripts import utils
import random
import json

class Github:
    def __init__(self):
        self.utils = utils.Utils()
        self.fetcher = resource_fetcher.ResourceFetcher()

    def extract_payload(self, response):
        for line in response.splitlines():
            if "type=\"application/json\"" in line:
                payload = line.split(">", 1)[1].split("<", 1)[0]

                try:
                    payload = json.loads(payload)
                    payload = payload["payload"]
                except:
                    continue

                return payload
        return None
        
    def get_commits(self, owner, repo, branch="main", start_commit=None, after=-1):
        if after > -1 and not start_commit:
            start_commit = self.get_commits(owner, repo, branch)["currentCommit"]["oid"]

        if after < 0:
            url = "https://github.com/{}/{}/commits/{}".format(owner, repo, branch)
        else:
            url = "https://github.com/{}/{}/commits/{}?after={}+{}".format(owner, repo, branch, start_commit, after)

        response = self.fetcher.fetch_and_parse_content(url)

        if not response:
            # The HTML page is unreachable (blocked or timing out): fall
            # back to the REST API and rebuild the historical payload
            # shape so callers keep working unchanged.
            return self._commits_via_api(owner, repo, branch, start_commit, after)

        payload = self.extract_payload(response)

        if not isinstance(payload, dict):
            raise ValueError("Cannot find commit information for repository {} on branch {}.".format(repo, branch))

        # GitHub now nests commit groups under "commitsRefRoute" in the
        # embedded JSON; older pages exposed "commitGroups" at top level.
        holder = payload.get("commitsRefRoute", payload)

        if not isinstance(holder, dict) or "commitGroups" not in holder:
            raise ValueError("Cannot find commit information for repository {} on branch {}.".format(repo, branch))

        # Preserve the historical return shape so callers can keep using
        # ["commitGroups"] and ["currentCommit"].
        if "currentCommit" not in holder and "currentCommit" in payload:
            holder["currentCommit"] = payload["currentCommit"]

        return holder

    def _commits_via_api(self, owner, repo, branch="main", start_commit=None, after=-1):
        """Rebuild the commits payload using the GitHub REST API."""
        url = "https://api.github.com/repos/{}/{}/commits?sha={}&per_page=30".format(owner, repo, branch)
        data = self._api_get(url)

        if not isinstance(data, list) or not data:
            raise ValueError("Cannot find commit information for repository {} on branch {}.".format(repo, branch))

        commits = []
        for entry in data:
            commit = entry.get("commit") or {}
            author = commit.get("author") or {}
            committer = commit.get("committer") or {}
            commits.append({
                "oid": entry.get("sha"),
                "committedDate": (committer.get("date") or author.get("date") or "").split("T")[0],
                "authoredDate": (author.get("date") or "").split("T")[0],
                "message": (commit.get("message") or "").split("\n")[0],
                "authors": [{"name": author.get("name", "")}],
                "committers": [{"name": committer.get("name", "")}],
            })

        current_sha = commits[0]["oid"]

        if after > -1 and start_commit:
            # Keep only the commits that follow start_commit.
            index = next((i for i, c in enumerate(commits) if c["oid"] == start_commit), None)
            if index is not None:
                commits = commits[index + 1:]

        return {
            "commitGroups": [{"commits": commits}],
            "currentCommit": {"oid": current_sha},
        }

    def get_release_tags(self, owner, repo):
        url = "https://github.com/{}/{}/releases".format(owner, repo)
        response = self.fetcher.fetch_and_parse_content(url)

        if not response:
            tags = [release.get("tag_name") for release in self.get_releases_via_api(owner, repo)]
            return [tag for tag in tags if tag]

        tags = []
        for line in response.splitlines():
            if "<a" in line and "href=\"" in line and "/releases/tag/" in line:
                tag = line.split("/releases/tag/")[1].split("\"")[0]
                if tag not in tags:
                    tags.append(tag)
        return tags

    # ------------------------------------------------------------------
    # GitHub REST API helpers.
    #
    # The HTML pages on github.com are frequently blocked or time out
    # (notably from mainland China), while api.github.com keeps working.
    # Every API call therefore goes through the same mirror fallback as
    # the release assets.
    # ------------------------------------------------------------------

    def _api_mirrors(self, url):
        return [
            "https://gh-proxy.com/{}".format(url),
            "https://ghproxy.net/{}".format(url),
            "https://ghfast.top/{}".format(url),
        ]

    def _api_get(self, url):
        return self.fetcher.fetch_and_parse_content(url, "json", mirrors=self._api_mirrors(url))

    def get_latest_commit_sha(self, owner, repo, branch="main"):
        """Return the newest commit SHA of a branch using the REST API."""
        url = "https://api.github.com/repos/{}/{}/commits?sha={}&per_page=1".format(owner, repo, branch)
        data = self._api_get(url)

        if isinstance(data, list) and data:
            sha = data[0].get("sha")
            if sha:
                return sha

        raise ValueError("Failed to fetch commit information for repository {} on branch {}.".format(repo, branch))

    def get_releases_via_api(self, owner, repo, per_page=30):
        """Return the releases of a repository as a list of dicts."""
        url = "https://api.github.com/repos/{}/{}/releases?per_page={}".format(owner, repo, per_page)
        data = self._api_get(url)

        return data if isinstance(data, list) else []

    def get_releases_normalized_via_api(self, owner, repo, per_page=30):
        """Return every release of a repository, normalized, in one request.

        Fetching each tag separately costs one request per release, which
        is slow and easily hits the API rate limit. This bulk variant is
        used when the caller only needs the list of releases.
        """
        releases = self.get_releases_via_api(owner, repo, per_page=per_page)

        return [self._normalize_api_release(release) for release in releases]

    def get_release_by_tag_via_api(self, owner, repo, tag_name):
        """Return a single release (tag, body, assets) using the REST API."""

        url = "https://api.github.com/repos/{}/{}/releases/tags/{}".format(owner, repo, tag_name)
        data = self._api_get(url)

        if not isinstance(data, dict) or "tag_name" not in data:
            raise ValueError("Failed to fetch release information from GitHub.")

        return self._normalize_api_release(data)

    def _normalize_api_release(self, release):
        assets = []
        for asset in release.get("assets", []) or []:
            url = asset.get("browser_download_url") or asset.get("url") or ""
            name = asset.get("name") or url.rsplit("/", 1)[-1]
            # Newer API responses expose a "digest" field of the form
            # "sha256:<hex>"; older ones have no digest at all.
            digest = asset.get("digest") or ""
            sha256 = digest.split("sha256:")[-1].strip() if "sha256:" in digest else None
            try:
                asset_id = int(asset.get("id"))
            except (TypeError, ValueError):
                asset_id = asset.get("id")
            assets.append({
                "product_name": self.extract_asset_name(name),
                "url": url,
                "name": name,
                "id": asset_id,
                "sha256": sha256,
            })

        return {
            "tag": release.get("tag_name"),
            "body": release.get("body") or "",
            "assets": assets,
        }

    def get_release_by_tag(self, owner, repo, tag_name):
        tag_url = "https://github.com/{}/{}/releases/tag/{}".format(owner, repo, tag_name)
        response = self.fetcher.fetch_and_parse_content(tag_url)

        if not response:
            return self.get_release_by_tag_via_api(owner, repo, tag_name)

        body = self._extract_body_content(response)

        release_tag_url = "https://github.com/{}/{}/releases/expanded_assets/{}".format(owner, repo, tag_name)
        response = self.fetcher.fetch_and_parse_content(release_tag_url)

        if not response:
            return self.get_release_by_tag_via_api(owner, repo, tag_name)

        assets = self._extract_assets(response)

        return {
            "tag": tag_name,
            "body": body,
            "assets": assets
        }

    def get_latest_release(self, owner, repo):
        url = "https://github.com/{}/{}/releases".format(owner, repo)
        response = self.fetcher.fetch_and_parse_content(url)

        if not response:
            releases = self.get_releases_via_api(owner, repo, per_page=1)
            if not releases:
                raise ValueError("Failed to fetch release information from GitHub.")
            return self._normalize_api_release(releases[0])

        tag_name = self._extract_tag_name(response)
        body = self._extract_body_content(response)

        release_tag_url = "https://github.com/{}/{}/releases/expanded_assets/{}".format(owner, repo, tag_name)
        response = self.fetcher.fetch_and_parse_content(release_tag_url)

        if not response:
            releases = self.get_releases_via_api(owner, repo, per_page=1)
            if not releases:
                raise ValueError("Failed to fetch expanded assets information from GitHub.")
            return self._normalize_api_release(releases[0])

        assets = self._extract_assets(response)

        return {
            "body": body,
            "assets": assets
        }

    def _extract_tag_name(self, response):
        for line in response.splitlines():
            if "<a" in line and "href=\"" in line and "/releases/tag/" in line:
                return line.split("/releases/tag/")[1].split("\"")[0]
        return None

    def _extract_body_content(self, response):
        for line in response.splitlines():
            if "<div" in line and "body-content" in line:
                return response.split(line.split(">", 1)[0], 1)[1].split("</div>", 1)[0][1:]
        return ""

    def _extract_assets(self, response):
        assets = []

        in_li_block = False

        for line in response.splitlines():

            if "<li" in line:
                in_li_block = True
                download_link = None
                sha256 = None
                asset_id = None
            elif in_li_block and "</li" in line:
                if download_link and asset_id:
                    assets.append({
                        "product_name": self.extract_asset_name(download_link.split("/")[-1]), 
                        "id": int(asset_id), 
                        "url": "https://github.com" + download_link,
                        "sha256": sha256
                    })
                in_li_block = False

            if in_li_block:  
                if download_link is None and "<a" in line and "href=\"" in line and "/releases/download" in line:
                    download_link = line.split("href=\"", 1)[1].split("\"", 1)[0]

                    if not ("tlwm" in download_link or ("tlwm" not in download_link and "RESEARCH" not in download_link.upper() and "DEBUG" not in download_link.upper())):
                        in_li_block = False
                        continue

                if sha256 is None and "sha256:" in line:
                    sha256 = line.split("sha256:", 1)[1].split("<", 1)[0]

                if asset_id is None and "<relative-time" in line:
                    asset_id = self._generate_asset_id(line)

        return assets

    def _generate_asset_id(self, line):
        try:
            return "".join(char for char in line.split("datetime=\"")[-1].split("\"")[0][::-1] if char.isdigit())[:9]
        except:
            return "".join(random.choices('0123456789', k=9))

    def extract_asset_name(self, file_name):
        if file_name.startswith("Realtek-AirPort-Family-") or file_name.startswith("Realtek.Airport.Family."):
            return "RealtekAirPortFamily"
        end_idx = len(file_name)
        if "-" in file_name:
            end_idx = min(file_name.index("-"), end_idx)
        if "_" in file_name:
            end_idx = min(file_name.index("_"), end_idx)
        if "." in file_name:
            end_idx = min(file_name.index("."), end_idx)
            if file_name[end_idx] == "." and file_name[end_idx - 1].isdigit():
                end_idx = end_idx - 1
        asset_name = file_name[:end_idx]

        if "Sniffer" in file_name:
            asset_name = file_name.split(".")[0]
        if asset_name == "IntelBluetooth":
            asset_name = "IntelBluetoothFirmware"
        if "unsupported" in file_name:
            asset_name += "-unsupported"
        elif "rtsx" in file_name:
            asset_name += "-rtsx"
        elif "itlwm" in file_name.lower():
            if "Sequoia" in file_name:
                asset_name += "24"
            elif "Tahoe" in file_name:
                asset_name += "25"
            elif "Sonoma14.4" in file_name:
                asset_name += "23.4"
            elif "Sonoma14.0" in file_name:
                asset_name += "23.0"
            elif "Ventura" in file_name:
                asset_name += "22"
            elif "Monterey" in file_name:
                asset_name += "21"
            elif "Big_Sur" in file_name:
                asset_name += "20"
            elif "Catalina" in file_name:
                asset_name += "19"
            elif "Mojave" in file_name:
                asset_name += "18"
            elif "High_Sierra" in file_name:
                asset_name += "17"

        return asset_name