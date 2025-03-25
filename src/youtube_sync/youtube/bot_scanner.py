import time
import traceback
import unicodedata
import warnings

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from youtube_sync.library import VidEntry  # Adjust if needed

URL = "https://www.youtube.com/@silverguru/videos"
URL_BASE = "https://www.youtube.com"

CACHE_OUTER_HTML: dict[str, str] = {}
_ERRORS = False


def sanitize_filepath(path: str, replacement_char: str = "_") -> str:
    path = unicodedata.normalize("NFKD", path).encode("ascii", "ignore").decode("ascii")
    invalid_chars = r'<>:"/\\|?*'
    for char in invalid_chars:
        path = path.replace(char, replacement_char)
    path = path.strip(". ")
    reserved_names = ["CON", "PRN", "AUX", "NUL"] + [
        f"{name}{i}" for name in ["COM", "LPT"] for i in range(1, 10)
    ]
    basename = path.split("/")[-1]
    if basename.upper() in reserved_names:
        path = path.replace(basename, replacement_char + basename)
    max_length = 255
    if len(path) > max_length:
        extension = "." + path.split(".")[-1] if "." in path else ""
        path = path[: max_length - len(extension)] + extension
    path = path.replace("'", "_")
    return path


def parse_youtube_videos(div_strs: list[str]) -> list[VidEntry]:
    global _ERRORS
    if _ERRORS:
        return []
    out: list[VidEntry] = []
    for div_str in div_strs:
        soup = BeautifulSoup(div_str, "html.parser")
        title_link = soup.find("a", id="video-title-link")
        try:
            title = title_link.get("title")  # type: ignore
            href = title_link.get("href")  # type: ignore
            assert title and href
            href = URL_BASE + str(href)
        except Exception:
            stack_trace = traceback.format_exc()
            warnings.warn(f"Error scraping video: {stack_trace}")
            continue
        out.append(VidEntry(title=str(title), url=href))
    return out


def fetch_all_sources(yt_channel_url: str, limit: int = -1) -> list[VidEntry]:
    global _ERRORS
    _ERRORS = False
    max_scrolls = limit if limit > 0 else 1000
    scroll_pause = 1
    index = 0

    print("starting browser")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(yt_channel_url)
        time.sleep(scroll_pause)

        last_height = page.evaluate("document.documentElement.scrollHeight")
        collected_html: set[str] = set()

        for i in range(max_scrolls):
            print("querying")
            elements = page.query_selector_all("ytd-rich-item-renderer")
            for el in elements:
                try:
                    html = el.inner_html()
                    if html not in collected_html:
                        collected_html.add(html)
                except Exception:
                    continue
            print("scrolling")
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            time.sleep(scroll_pause)
            new_height = page.evaluate("document.documentElement.scrollHeight")
            if abs(new_height - last_height) < 100:
                break
            last_height = new_height
            print(f"#### {index}: scrolling for new content ####")
            index += 1

        browser.close()
        return list_vids_from_html(collected_html)


def list_vids_from_html(html_blocks: set[str]) -> list[VidEntry]:
    all_vids: list[VidEntry] = []
    for block in html_blocks:
        vids = parse_youtube_videos([block])
        all_vids.extend(vids)
    # Deduplicate by URL
    seen = set()
    unique_vids = []
    for vid in all_vids:
        if vid.url not in seen:
            seen.add(vid.url)
            unique_vids.append(vid)
    return unique_vids


def test_channel_url(channel_url: str) -> bool:
    try:
        response = requests.get(channel_url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def scan_vids(yt_channel_url: str, limit: int | None) -> list[VidEntry]:
    """
    Fetch YouTube video entries from a channel page using Playwright.
    yt_channel_url should be something like: https://www.youtube.com/@channel/videos
    """
    if not test_channel_url(yt_channel_url):
        raise ValueError(f"Invalid channel URL: {yt_channel_url}")

    limit = limit if limit is not None else -1
    vids = fetch_all_sources(yt_channel_url=yt_channel_url, limit=limit)

    # Dedup again just in case
    seen: set[str] = set()
    unique_vids: list[VidEntry] = []
    for vid in vids:
        if vid.url not in seen:
            seen.add(vid.url)
            unique_vids.append(vid)

    return unique_vids


def main() -> int:
    if not test_channel_url(URL):
        raise ValueError(f"Invalid channel URL: {URL}")
    vids = fetch_all_sources(URL, limit=1)
    print(f"Found {len(vids)} videos:")
    for vid in vids:
        print(f"  {vid.title} -> {vid.url}")
    return 0


if __name__ == "__main__":
    main()
