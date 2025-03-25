import logging
import pickle
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from filelock import FileLock

from youtube_sync.open_webdriver import open_webdriver  # type: ignore

from .types import Source

# Set up module logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

COOKIE_REFRESH_SECONDS = 2 * 60 * 60  # 2 hours


def set_cookie_refresh_seconds(seconds: int) -> None:
    global COOKIE_REFRESH_SECONDS
    COOKIE_REFRESH_SECONDS = seconds


def _convert_cookies_to_txt(cookies: list[dict]) -> str:
    """
    Convert a list of cookie dictionaries to the cookies.txt (Netscape format).

    Each cookie dictionary may contain the following keys:
      - domain: The domain for the cookie.
      - expiry: Unix timestamp for expiration. If missing, treated as a session cookie (0).
      - httpOnly: (Ignored in this format)
      - name: The name of the cookie.
      - path: The URL path for which the cookie is valid.
      - sameSite: (Ignored in this format)
      - secure: Boolean indicating if the cookie is secure.
      - value: The cookie's value.

    Returns:
      A string formatted as a cookies.txt file.
    """
    # Header lines for the cookies.txt file
    lines: list[str] = [
        "# Netscape HTTP Cookie File",
        "# http://curl.haxx.se/rfc/cookie_spec.html\n",
    ]

    # Iterate over each cookie dictionary and convert to the correct format.
    for cookie in cookies:
        domain: str = cookie.get("domain", "")
        # If the domain starts with a dot, it applies to subdomains.
        flag: str = "TRUE" if domain.startswith(".") else "FALSE"
        path: str = cookie.get("path", "/")
        # Secure field: 'TRUE' if cookie is secure, otherwise 'FALSE'
        secure: str = "TRUE" if cookie.get("secure", False) else "FALSE"
        # Use expiry if provided; otherwise, set to 0 for a session cookie.
        expiry: str = str(cookie.get("expiry", 0))
        name: str = cookie.get("name", "")
        value: str = cookie.get("value", "")

        # Create a tab-separated line in the cookies.txt format.
        line: str = f"{domain}\t{flag}\t{path}\t{secure}\t{expiry}\t{name}\t{value}"
        lines.append(line)

    # Join all lines with newline characters.
    return "\n".join(lines)


def _get_cookies_from_browser_using_webdriver(url: str) -> list[dict]:
    with open_webdriver(disable_gpu=True) as driver:
        # clear cookies
        driver.delete_all_cookies()
        driver.get(url)
        return driver.get_cookies()


def _get_cookies_from_browser_using_playwright(url: str) -> list[dict]:
    from .playwright_launcher import Page, launch_playwright, set_headless

    set_headless(True)
    out: list[dict] = []

    page: Page
    with launch_playwright() as (page, _):
        page.goto(url)
        cookies = page.context.cookies()
        # convert to list of dicts
        out = [dict(c) for c in cookies]
        return out


def _get_cookies_from_browser(url: str) -> list[dict]:
    # return _get_cookies_from_browser_using_webdriver(url=url)
    return _get_cookies_from_browser_using_playwright(url=url)


def _get_platform_homepage_url(source: Source) -> str:
    if source == Source.YOUTUBE:
        return "https://www.youtube.com"
    if source == Source.RUMBLE:
        return "https://rumble.com"
    if source == Source.BRIGHTEON:
        return "https://www.brighteon.com"
    raise ValueError(f"Unknown source: {source}")


_COOKIE_ROOT_PATH = Path("cookies")


def set_cookie_root_path(path: Path):
    global _COOKIE_ROOT_PATH
    _COOKIE_ROOT_PATH = path


@dataclass
class CookiePaths:
    pkl: Path
    txt: Path
    lck: Path

    @staticmethod
    def create(source: Source) -> "CookiePaths":
        base_path = _COOKIE_ROOT_PATH / source.value
        out = CookiePaths(
            pkl=base_path / "cookies.pkl",
            txt=base_path / "cookies.txt",
            lck=base_path / "cookies.lock",
        )
        return out


def get_cookie_paths(source: Source) -> CookiePaths:
    if source == Source.YOUTUBE:
        return CookiePaths.create(Source.YOUTUBE)
    if source == Source.RUMBLE:
        return CookiePaths.create(Source.RUMBLE)
    if source == Source.BRIGHTEON:
        return CookiePaths.create(Source.BRIGHTEON)
    raise ValueError(f"Unknown source: {source}")


def get_or_refresh_cookies(
    source: Source,
    cookies: "Cookies | None",
) -> "Cookies":

    paths = get_cookie_paths(source)

    with FileLock(paths.lck):
        now = datetime.now()
        cookies_pkl = paths.pkl
        cookies_txt = paths.txt
        # case 1: we have cookies
        if cookies is not None:
            # and they are not expired
            expire_time = cookies.creation_time + timedelta(
                seconds=COOKIE_REFRESH_SECONDS
            )
            if now < expire_time:
                return cookies
        # case 2: we have cookies on disk, but we must check to see that they are the right type.
        if cookies_pkl.exists() and cookies_txt.exists():
            try:
                yt_cookies = Cookies.from_pickle(cookies_pkl)
                if isinstance(yt_cookies, Cookies):
                    seconds_old = (now - yt_cookies.creation_time).seconds
                    if seconds_old < COOKIE_REFRESH_SECONDS:
                        # save the cookies to the new location
                        yt_cookies.save(cookies_pkl)
                        yt_cookies.save(cookies_txt)
                        return yt_cookies
                else:
                    logger.warning("Invalid cookies found at %s", cookies_pkl)
            except Exception as e:
                logger.error("Error loading cookies from %s: %s", cookies_pkl, e)
        # case 3: we have no cookies, or they are expired, or they are the wrong type
        yt_cookies = Cookies.from_browser(source, save=True)
        return yt_cookies


class Cookies:

    @staticmethod
    def get_or_refresh(source: Source, cookies: "Cookies | None") -> "Cookies":

        return get_or_refresh_cookies(source=source, cookies=cookies)

    @staticmethod
    def from_browser(source: Source, save=True) -> "Cookies":
        print("\n############################")
        print(f"# Getting cookies for {source}")
        print("#############################\n")
        url: str = _get_platform_homepage_url(source)
        data = _get_cookies_from_browser(url=url)
        out = Cookies(source=source, data=data)
        if save:
            out.save(out.path_pkl)
            out.save(out.path_txt)
        return out

    def refresh(self) -> None:
        new_self = Cookies.get_or_refresh(source=self.source, cookies=self)
        if new_self != self:
            self.data = new_self.data
            self.creation_time = new_self.creation_time

    def __init__(self, source: Source, data: list[dict]) -> None:
        self.version = "1"
        self.data = data
        self.source = source
        path: CookiePaths = get_cookie_paths(source)
        self.path_pkl = path.pkl
        self.path_txt = path.txt
        self.path_lock = path.lck
        self.creation_time = datetime.now()

    @property
    def cookies_txt(self) -> str:
        return _convert_cookies_to_txt(self.data)

    def write_cookies_txt(self, file_path: Path):
        file_path.write_text(self.cookies_txt, encoding="utf-8")

    @staticmethod
    def load(source: Source) -> "Cookies":
        cookies = Cookies.get_or_refresh(source=source, cookies=None)
        return cookies

    def save(self, out_file: Path) -> None:
        # assert out_pickle_file.suffix == ".pkl"
        # self.to_pickle(out_pickle_file)
        suffix = out_file.suffix
        if suffix not in {".pkl", ".txt"}:
            raise ValueError(
                f"Unsupported file extension: {suffix}, options are: '.pkl', '.txt'"
            )
        parent = out_file.parent
        parent.mkdir(parents=True, exist_ok=True)
        if suffix == ".pkl":
            logger.debug("Saving cookies to %s", out_file)
            self.to_pickle(out_file)
        elif suffix == ".txt":
            logger.debug("Saving cookies to %s", out_file)
            self.write_cookies_txt(out_file)
        else:
            raise ValueError(f"Unsupported file extension: {suffix}")

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterator[dict]:
        return iter(self.data)

    def __repr__(self) -> str:
        return f"Cookies({self.data})"

    def __str__(self) -> str:
        return self.cookies_txt

    def to_pickle(self, file_path: Path) -> None:
        """
        Serialize the Cookies object to a pickle file.

        Args:
            file_path: Path where the pickle file will be saved
        """
        with open(file_path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def from_pickle(file_path: Path) -> "Cookies":
        """
        Create a Cookies object from a pickle file.

        Args:
            file_path: Path to the pickle file

        Returns:
            A Cookies object with data loaded from the pickle file

        Raises:
            FileNotFoundError: If the pickle file doesn't exist
            pickle.UnpicklingError: If the file contains invalid pickle data
        """
        with open(file_path, "rb") as f:
            return pickle.load(f)
