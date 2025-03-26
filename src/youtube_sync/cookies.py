import logging
import pickle
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from filelock import FileLock

from youtube_sync.open_webdriver import open_webdriver  # type: ignore

from .logutil import create_logger
from .types import Source

# Set up module logger
logger = create_logger(__name__, logging.getLogger().level)

COOKIE_REFRESH_SECONDS = 2 * 60 * 60  # 2 hours


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
    logger.info("Getting cookies using WebDriver from %s", url)
    try:
        with open_webdriver(disable_gpu=True) as driver:
            # clear cookies
            driver.delete_all_cookies()
            logger.debug("Navigating to %s", url)
            driver.get(url)
            cookies = driver.get_cookies()
            logger.info("Retrieved %d cookies from WebDriver", len(cookies))
            return cookies
    except Exception as e:
        logger.error("Error getting cookies with WebDriver: %s", str(e))
        raise


def _get_cookies_from_browser_using_playwright(url: str) -> list[dict]:
    from .playwright_launcher import Page, launch_playwright, set_headless

    logger.info("Getting cookies using Playwright from %s", url)
    set_headless(True)
    out: list[dict] = []

    try:
        page: Page
        with launch_playwright() as (page, _):
            logger.debug("Navigating to %s", url)
            page.goto(url)
            cookies = page.context.cookies()
            # convert to list of dicts
            out = [dict(c) for c in cookies]
            logger.info("Retrieved %d cookies from Playwright", len(out))
            return out
    except Exception as e:
        logger.error("Error getting cookies with Playwright: %s", str(e))
        raise


def _get_cookies_from_browser(url: str) -> list[dict]:
    logger.info("Getting cookies from browser for %s", url)
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
    with COOKIES_LOCK:
        global COOKIES
        COOKIES = {}
        logger.info("Cleared COOKIES cache")


@dataclass
class CookiePaths:
    pkl: str
    txt: str
    lck: str

    @staticmethod
    def create(source: Source) -> "CookiePaths":
        base_path = _COOKIE_ROOT_PATH / source.value
        out = CookiePaths(
            pkl=(base_path / "cookies.pkl").as_posix(),
            txt=(base_path / "cookies.txt").as_posix(),
            lck=(base_path / "cookies.lock").as_posix(),
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


def _get_or_refresh_cookies(
    source: Source,
    cookies: "Cookies | None",
) -> "Cookies":
    logger.info("Getting or refreshing cookies for %s", source.value)

    paths = get_cookie_paths(source)
    logger.debug(
        "Cookie paths: pkl=%s, txt=%s, lock=%s", paths.pkl, paths.txt, paths.lck
    )

    with FileLock(paths.lck):
        logger.debug("Acquired lock for cookie refresh: %s", paths.lck)
        now = datetime.now()
        cookies_pkl = paths.pkl
        cookies_txt = paths.txt

        # case 1: we have cookies in memory
        if cookies is not None:
            # and they are not expired
            expire_time = cookies.creation_time + timedelta(
                seconds=COOKIE_REFRESH_SECONDS
            )
            if now < expire_time:
                logger.info(
                    "Using existing cookies (not expired, age: %d seconds)",
                    (now - cookies.creation_time).seconds,
                )
                return cookies
            else:
                logger.info(
                    "Existing cookies expired (age: %d seconds)",
                    (now - cookies.creation_time).seconds,
                )
        else:
            logger.debug("No cookies provided in memory")

        # case 2: we have cookies on disk, but we must check to see that they are the right type.
        if Path(cookies_pkl).exists() and Path(cookies_txt).exists():
            logger.debug("Found cookie files on disk")

            yt_cookies: Cookies | None = None
            try:
                yt_cookies = Cookies.from_pickle(cookies_pkl)
            except Exception as e:
                logger.error("Error loading cookies from %s: %s", cookies_pkl, e)
                yt_cookies = Cookies.from_txt(source, Path(cookies_txt).read_text())
            try:
                yt_cookies = Cookies.from_pickle(cookies_pkl)
                if isinstance(yt_cookies, Cookies):
                    seconds_old = (now - yt_cookies.creation_time).seconds
                    logger.debug(
                        "Loaded cookies from disk, age: %d seconds", seconds_old
                    )

                    if seconds_old < COOKIE_REFRESH_SECONDS:
                        logger.info(
                            "Using cookies from disk (not expired, age: %d seconds)",
                            seconds_old,
                        )
                        # save the cookies to the new location
                        yt_cookies.save(cookies_pkl)
                        yt_cookies.save(cookies_txt)
                        return yt_cookies
                    else:
                        logger.info(
                            "Cookies from disk expired (age: %d seconds)", seconds_old
                        )
                else:
                    logger.warning("Invalid cookies found at %s", cookies_pkl)
            except Exception as e:
                logger.error("Error loading cookies from %s: %s", cookies_pkl, e)

        # case 3: we have no cookies, or they are expired, or they are the wrong type
        logger.info("Fetching fresh cookies from browser for %s", source.value)
        yt_cookies = Cookies.from_browser(source, save=True)
        logger.info("Successfully obtained %d fresh cookies", len(yt_cookies))
        return yt_cookies


COOKIES: dict[Source, "Cookies"] = {}
COOKIES_LOCK = threading.Lock()


def get_or_refresh_cookies(
    source: Source,
    cookies: "Cookies | None",
) -> "Cookies":
    global COOKIES

    with COOKIES_LOCK:
        if source not in COOKIES:
            logger.info("Creating new Cookies object for %s", source.value)
            COOKIES[source] = _get_or_refresh_cookies(source=source, cookies=cookies)
        return COOKIES[source]


def set_cookie_refresh_seconds(seconds: int) -> None:
    global COOKIE_REFRESH_SECONDS
    COOKIE_REFRESH_SECONDS = seconds


class Cookies:

    @staticmethod
    def get_or_refresh(source: Source, cookies: "Cookies | None") -> "Cookies":

        return get_or_refresh_cookies(source=source, cookies=cookies)

    @staticmethod
    def from_txt(source: Source, txt: str) -> "Cookies":
        return Cookies(source=source, text=txt)

    @staticmethod
    def from_browser(source: Source, save=True) -> "Cookies":
        logger.info("\n############################")
        logger.info("# Getting cookies for %s", source)
        logger.info("#############################")

        url: str = _get_platform_homepage_url(source)
        logger.debug("Using platform URL: %s", url)

        data = _get_cookies_from_browser(url=url)
        logger.info("Retrieved %d cookies from browser", len(data))

        text = _convert_cookies_to_txt(data)

        out = Cookies(source=source, text=text)
        if save:
            logger.info("Saving cookies to disk")
            out.save(Path(out.path_pkl))
            out.save(Path(out.path_txt))
        return out

    def refresh(self) -> None:
        # logger.info("Refreshing cookies for %s", self.source.value)
        new_self = Cookies.get_or_refresh(source=self.source, cookies=self)
        if new_self != self:
            logger.info("Cookies were refreshed, updating instance")
            self._cookies_txt = new_self.cookies_txt
            self.creation_time = new_self.creation_time
        else:
            logger.debug("No cookie refresh needed")

    def __init__(self, source: Source, text: str) -> None:
        self.version = "1"
        # self.data = data
        self.source = source
        path: CookiePaths = get_cookie_paths(source)
        self.path_pkl = path.pkl
        self.path_txt = path.txt
        self.path_lock = path.lck
        self.creation_time = datetime.now()
        self._cookies_txt = text

    @property
    def cookies_txt(self) -> str:
        return self._cookies_txt

    def write_cookies_txt(self, file_path: Path):
        file_path.write_text(self.cookies_txt, encoding="utf-8")

    @staticmethod
    def load(source: Source) -> "Cookies":
        cookies = Cookies.get_or_refresh(source=source, cookies=None)
        return cookies

    def save(self, out_file: Path | str) -> None:
        # assert out_pickle_file.suffix == ".pkl"
        # self.to_pickle(out_pickle_file)
        if isinstance(out_file, str):
            out_file = Path(out_file)
        suffix = out_file.suffix
        if suffix not in {".pkl", ".txt"}:
            error_msg = (
                f"Unsupported file extension: {suffix}, options are: '.pkl', '.txt'"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        parent = out_file.parent
        if not parent.exists():
            logger.debug("Creating directory: %s", parent)
            parent.mkdir(parents=True, exist_ok=True)

        if suffix == ".pkl":
            logger.info(
                "Saving %d cookies to pickle file: %s",
                len(self.cookies_txt.splitlines()),
                out_file,
            )
            self.to_pickle(out_file)
        elif suffix == ".txt":
            logger.info(
                "Saving %d cookies to text file: %s",
                len(self.cookies_txt.splitlines()),
                out_file,
            )
            self.write_cookies_txt(out_file)
        else:
            error_msg = f"Unsupported file extension: {suffix}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug("Successfully saved cookies to %s", out_file)

    def __len__(self) -> int:
        return len(self.cookies_txt.splitlines())

    def __repr__(self) -> str:
        return f"Cookies({self.cookies_txt})"

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
    def from_pickle(file_path: Path | str) -> "Cookies":
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
        if isinstance(file_path, str):
            file_path = Path(file_path)
        logger.debug("Loading cookies from pickle file: %s", file_path)
        if not file_path.exists():
            error_msg = f"Cookie file not found: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(file_path, "rb") as f:
                cookies = pickle.load(f)
                logger.info(
                    "Successfully loaded %d cookies from %s",
                    len(cookies.data) if hasattr(cookies, "data") else 0,
                    file_path,
                )
                return cookies
        except Exception as e:
            logger.error("Failed to load cookies from %s: %s", file_path, str(e))
            raise
