"""Shared HTTP fetcher using Docker curl-impersonate + BeautifulSoup.

Usage:
    from fetch import fetch, fetch_soup

    html = fetch("https://wol.jw.org/tvl/wol/b/r153/lp-vl/nwt/1/1")
    soup = fetch_soup("https://wol.jw.org/tvl/wol/b/r153/lp-vl/nwt/1/1")
"""

import subprocess
import time
import sys
from bs4 import BeautifulSoup

DOCKER_IMAGE = "lwthiker/curl-impersonate:0.6-ff"
DOCKER_WRAPPER = "curl_ff117"
DELAY = 2  # seconds between requests

_last_request_time = 0.0


def fetch(url: str, timeout: int = 30, retries: int = 3) -> str | None:
    """Fetch a URL using Docker curl-impersonate. Returns HTML string or None."""
    global _last_request_time

    # Rate limiting
    elapsed = time.time() - _last_request_time
    if elapsed < DELAY:
        time.sleep(DELAY - elapsed)

    for attempt in range(retries):
        try:
            result = subprocess.run(
                [
                    "docker", "run", "--rm",
                    DOCKER_IMAGE,
                    DOCKER_WRAPPER,
                    "-s",  # silent
                    "-L",  # follow redirects
                    "--max-time", str(timeout),
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 10,
            )
            _last_request_time = time.time()

            if result.returncode == 0 and result.stdout:
                return result.stdout
            elif result.returncode == 22:  # HTTP error (404 etc)
                return None
            else:
                wait = DELAY * (2 ** attempt)
                print(f"  fetch retry {attempt+1}/{retries} (exit {result.returncode}) "
                      f"waiting {wait}s: {url}", file=sys.stderr)
                if result.stderr:
                    print(f"    stderr: {result.stderr[:200]}", file=sys.stderr)
                time.sleep(wait)
        except subprocess.TimeoutExpired:
            wait = DELAY * (2 ** attempt)
            print(f"  fetch timeout retry {attempt+1}/{retries} waiting {wait}s: {url}",
                  file=sys.stderr)
            time.sleep(wait)
        except Exception as e:
            print(f"  fetch error: {e}", file=sys.stderr)
            return None

    return None


def fetch_soup(url: str, parser: str = "html5lib", **kwargs) -> BeautifulSoup | None:
    """Fetch a URL and return a BeautifulSoup object."""
    html = fetch(url, **kwargs)
    if html is None:
        return None
    return BeautifulSoup(html, parser)


def fetch_and_save(url: str, filepath: str, **kwargs) -> str | None:
    """Fetch a URL, save the raw HTML to a file, and return the HTML.

    If the file already exists and is non-empty, reads from disk instead
    of re-fetching (resume support).
    """
    from pathlib import Path
    p = Path(filepath)
    if p.exists() and p.stat().st_size > 0:
        return p.read_text()
    html = fetch(url, **kwargs)
    if html is not None:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html)
    return html


def fetch_many(urls: list[str], desc: str = "Fetching") -> list[tuple[str, str | None]]:
    """Fetch multiple URLs with progress bar. Returns list of (url, html_or_none).

    Rate limiting is handled by fetch() internally.
    """
    from tqdm import tqdm
    results = []
    for url in tqdm(urls, desc=desc):
        html = fetch(url)
        results.append((url, html))
    return results
