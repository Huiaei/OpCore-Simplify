from Scripts import integrity_checker
from Scripts import utils
import ssl
import os
import json
import plistlib
import socket
import sys
import gzip
import zlib
import time
import http.client

if sys.version_info >= (3, 0):
    from urllib.request import urlopen, Request
    from urllib.error import URLError
else:
    import urllib2
    from urllib2 import urlopen, Request, URLError

MAX_ATTEMPTS = 3

class ResourceFetcher:
    def __init__(self, headers=None):
        self.request_headers = headers or {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }
        self.buffer_size = 16 * 1024
        # Reading from the slow mirror proxies can stall for far longer than
        # the 10s used for plain API/page fetches - a short timeout there would
        # abort every large kext download.
        self.download_timeout = 30
        self.ssl_context = self.create_ssl_context()
        self.integrity_checker = integrity_checker.IntegrityChecker()
        self.utils = utils.Utils()

    def create_ssl_context(self):
        try:
            cafile = ssl.get_default_verify_paths().openssl_cafile
            if not os.path.exists(cafile):
                import certifi
                cafile = certifi.where()
            ssl_context = ssl.create_default_context(cafile=cafile)
        except Exception as e:
            print("Failed to create SSL context: {}".format(e))
            ssl_context = ssl._create_unverified_context()
        return ssl_context

    def _make_request(self, resource_url, timeout=10, extra_headers=None):
        try:
            headers = dict(self.request_headers)
            headers["Accept-Encoding"] = "gzip, deflate"
            if extra_headers:
                headers.update(extra_headers)
            
            return urlopen(Request(resource_url, headers=headers), timeout=timeout, context=self.ssl_context)
        except socket.timeout as e:
            print("Timeout error: {}".format(e))
        except ssl.SSLError as e:
            print("SSL error: {}".format(e))
        except (URLError, socket.gaierror) as e:
            print("Connection error: {}".format(e))
        except Exception as e:
            print("Request failed: {}".format(e))

        return None

    def _get_github_mirrors(self, resource_url):
        """Return proxy mirrors for a GitHub-hosted download.

        GitHub release assets (github.com/.../releases/download/...) are often
        unreachable or extremely slow, while the raw.githubusercontent.com and
        codeload paths still work. These public proxies serve the very same
        file and are used as fallbacks only.
        """
        if "github.com" not in resource_url:
            return []

        proxies = (
            "https://gh-proxy.com/",
            "https://ghproxy.net/",
            "https://ghfast.top/",
            "https://mirror.ghproxy.com/",
        )

        return ["{}{}".format(proxy, resource_url) for proxy in proxies]

    def _get_raw_mirrors(self, resource_url):
        """Return mirrors for a raw.githubusercontent.com download.

        The raw content host is regularly blocked or times out. jsDelivr
        serves the exact same repository content through its own CDN.
        """
        if "raw.githubusercontent.com" not in resource_url:
            return []

        prefix = resource_url.split("raw.githubusercontent.com/", 1)[1]
        parts = prefix.split("/")
        if len(parts) < 3:
            return []
        owner_repo = "/".join(parts[:2])
        rest = "/".join(parts[2:])
        branch = ""
        path = rest
        if "/" in rest:
            head, tail = rest.split("/", 1)
            branch, path = head, tail

        mirrors = []
        if branch and path:
            for cdn in ("https://cdn.jsdelivr.net/gh/", "https://fastly.jsdelivr.net/gh/", "https://gcore.jsdelivr.net/gh/"):
                mirrors.append("{}{}@{}/{}".format(cdn, owner_repo, branch, path))
        else:
            for cdn in ("https://cdn.jsdelivr.net/gh/", "https://fastly.jsdelivr.net/gh/", "https://gcore.jsdelivr.net/gh/"):
                mirrors.append("{}{}/{}".format(cdn, owner_repo, path))

        for proxy in ("https://gh-proxy.com/", "https://ghproxy.net/"):
            mirrors.append("{}{}".format(proxy, resource_url))

        return mirrors

    def _get_all_mirrors(self, resource_url):
        """Return every applicable mirror for a download URL.

        Combines the GitHub release-asset proxies with the raw-content CDN
        mirrors, so callers do not need to know which host serves the file.
        """
        mirrors = []
        for mirror in self._get_github_mirrors(resource_url) + self._get_raw_mirrors(resource_url):
            if mirror not in mirrors:
                mirrors.append(mirror)
        return mirrors

    def _get_dortania_mirrors(self):
        return [
            "https://raw.githubusercontent.com/dortania/build-repo/builds/latest.json",
            "https://fastly.jsdelivr.net/gh/dortania/build-repo@builds/latest.json",
            "https://cdn.jsdelivr.net/gh/dortania/build-repo@builds/latest.json",
            "https://gcore.jsdelivr.net/gh/dortania/build-repo@builds/latest.json",
            "https://gh-proxy.com/https://raw.githubusercontent.com/dortania/build-repo/builds/latest.json",
            "https://ghfast.top/https://raw.githubusercontent.com/dortania/build-repo/builds/latest.json",
        ]

    def fetch_and_parse_content(self, resource_url, content_type=None, mirrors=None):
        candidate_urls = [resource_url] + list(mirrors or [])
        response = None
        content = None
        tried = []

        for url in candidate_urls:
            attempt = 0
            while attempt < MAX_ATTEMPTS:
                attempt += 1
                response = self._make_request(url)

                if not response:
                    print("Failed to fetch content from {}. Retrying...".format(url))
                    continue

                try:
                    if response.getcode() != 200:
                        raise URLError("HTTP {}".format(response.getcode()))
                    # The body read happens after the headers arrived, so it can
                    # still stall or drop halfway through a large page - treat
                    # that as a failed attempt instead of letting it escape.
                    content = response.read()
                except (OSError, http.client.HTTPException, URLError) as e:
                    print("Failed to read content from {}: {}. Retrying...".format(url, e))
                    content = None
                    try:
                        response.close()
                    except Exception:
                        pass
                    continue

                break

            if content is not None:
                break

            response = None
            tried.append(url)

        if content is None:
            print("Failed to fetch content from {} (tried: {})".format(resource_url, ", ".join(tried) or resource_url))
            return None

        if response.info().get("Content-Encoding") == "gzip" or content.startswith(b"\x1f\x8b"):
            try:
                content = gzip.decompress(content)
            except Exception as e:
                print("Failed to decompress gzip content: {}".format(e))
        elif response.info().get("Content-Encoding") == "deflate":
            try:
                content = zlib.decompress(content)
            except Exception as e:
                print("Failed to decompress deflate content: {}".format(e))
        
        try:
            if content_type == "json":
                return json.loads(content)
            elif content_type == "plist":
                return plistlib.loads(content)
            else:
                return content.decode("utf-8")
        except Exception as e:
            print("Error parsing content as {}: {}".format(content_type, e))
            
        return None

    def _download_with_progress(self, response, local_file):
        total_size = response.getheader("Content-Length")
        if total_size:
            total_size = int(total_size)
        bytes_downloaded = 0
        start_time = time.time()
        last_time = start_time
        last_bytes = 0
        speeds = []

        try:
            "█░".encode(getattr(sys.stdout, "encoding", None) or "utf-8")
            full_block, empty_block = "█", "░"
        except (UnicodeEncodeError, LookupError, TypeError):
            # Stock Windows consoles (e.g. cp1252) cannot encode
            # block-drawing glyphs; degrade to ASCII.
            full_block, empty_block = "#", "-"

        speed_str = "-- KB/s"
        
        while True:
            chunk = response.read(self.buffer_size)
            if not chunk:
                break
            local_file.write(chunk)
            bytes_downloaded += len(chunk)
            
            current_time = time.time()
            time_diff = current_time - last_time
            
            if time_diff > 0.5:
                current_speed = (bytes_downloaded - last_bytes) / time_diff
                speeds.append(current_speed)
                if len(speeds) > 5:
                    speeds.pop(0)
                avg_speed = sum(speeds) / len(speeds)
                
                if avg_speed < 1024*1024:
                    speed_str = "{:.1f} KB/s".format(avg_speed/1024)
                else:
                    speed_str = "{:.1f} MB/s".format(avg_speed/(1024*1024))
                
                last_time = current_time
                last_bytes = bytes_downloaded
            
            if total_size:
                percent = int(bytes_downloaded / total_size * 100)
                bar_length = 40
                filled = int(bar_length * bytes_downloaded / total_size)
                bar = full_block * filled + empty_block * (bar_length - filled)
                progress = "{} [{}] {:3d}% {:.1f}/{:.1f}MB".format(speed_str, bar, percent, bytes_downloaded/(1024*1024), total_size/(1024*1024))
            else:
                progress = "{} {:.1f}MB downloaded".format(speed_str, bytes_downloaded/(1024*1024))
            
            print(" " * 80, end="\r")
            print(progress, end="\r")
            
        print()

    def download_and_save_file(self, resource_url, destination_path, sha256_hash=None, mirrors=None):
        candidate_urls = [resource_url] + list(mirrors or [])

        for url in candidate_urls:
            if self._download_with_retries(url, destination_path, sha256_hash):
                return True

        print("Failed to download {} after {} attempts.".format(resource_url, MAX_ATTEMPTS))
        if os.path.exists(destination_path):
            try:
                os.remove(destination_path)
            except OSError:
                pass
        return False

    def _download_with_retries(self, resource_url, destination_path, sha256_hash=None):
        attempt = 0

        while attempt < MAX_ATTEMPTS:
            attempt += 1

            # Keep whatever arrived last time and ask for the rest of it - the
            # public proxy mirrors drop the connection every few megabytes, and
            # restarting a 10 MB file from zero never finishes on a slow link.
            resume_from = os.path.getsize(destination_path) if os.path.exists(destination_path) else 0
            extra_headers = {"Range": "bytes={}-".format(resume_from)} if resume_from else None

            response = self._make_request(resource_url, timeout=self.download_timeout, extra_headers=extra_headers)

            if not response:
                print("Failed to fetch content from {}. Retrying...".format(resource_url))
                if resume_from and os.path.exists(destination_path):
                    # The range request itself was rejected (416 and friends) -
                    # drop the partial file so the next attempt starts clean.
                    try:
                        os.remove(destination_path)
                    except OSError:
                        pass
                continue

            append = False
            if resume_from:
                if response.getcode() == 206:
                    append = True
                    print("Resuming download at {} bytes...".format(resume_from))
                else:
                    print("Server ignored the range request - starting over.")

            try:
                with open(destination_path, "ab" if append else "wb") as local_file:
                    self._download_with_progress(response, local_file)
            except (OSError, http.client.HTTPException) as e:
                # A stall or drop halfway through is not fatal - keep the bytes
                # that did arrive and resume from there on the next attempt.
                try:
                    response.close()
                except Exception:
                    pass
                print("")
                print("Download interrupted ({}). Retrying...".format(e))
                continue

            if os.path.exists(destination_path) and os.path.getsize(destination_path) > 0:
                if sha256_hash:
                    print("Verifying SHA256 checksum...")
                    downloaded_hash = self.integrity_checker.get_sha256(destination_path)
                    if downloaded_hash.lower() == sha256_hash.lower():
                        print("Checksum verified successfully.")
                        return True
                    else:
                        print("Checksum mismatch! Removing file and retrying download...")
                        os.remove(destination_path)
                        continue
                else:
                    print("No SHA256 hash provided. Downloading file without verification.")
                    return True
            
            if os.path.exists(destination_path) and os.path.getsize(destination_path) == 0:
                os.remove(destination_path)

            if attempt < MAX_ATTEMPTS:
                print("Download failed for {}. Retrying...".format(resource_url))

        return False