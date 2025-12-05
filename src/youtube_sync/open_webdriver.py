import os
import sys
import traceback
from typing import Optional

import filelock  # type: ignore
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.remote.webdriver import WebDriver as Driver  # type: ignore
from webdriver_manager.chrome import ChromeDriverManager

# from open_webdriver.path import LOG_FILE, WDM_DIR
WDM_DIR = os.path.join(os.path.expanduser("~"), ".wdm")
LOG_FILE = os.path.join(WDM_DIR, "log.txt")

INSTALL_TIMEOUT = float(60 * 10)  # Up to 10 minutes of install time.
FORCE_HEADLESS = sys.platform == "linux" and "DISPLAY" not in os.environ

os.makedirs(WDM_DIR, exist_ok=True)
LOCK_FILE = os.path.join(WDM_DIR, "lock.file")


def _user_agent(chrome_version: str | None = None) -> str:
    """Gets the user agent."""
    chrome_version = chrome_version or "114.0.5735.90"
    return (
        f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        f"Chrome/{chrome_version} Safari/537.36"
    )


def _init_log() -> None:
    """Initializes the log."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, encoding="utf-8", mode="w") as filed:
        filed.write(f"{__file__}: Starting up web driver.\n")
        if sys.platform == "linux":
            if os.geteuid() == 0:
                filed.write("\n\n  WARNING: Running as root. The driver may crash!\n\n")


_IS_DOCKER = True


def _make_options(
    headless: bool,
    user_agent: str | None,
    disable_gpu: bool = True,
    disable_dev_shm_usage: bool = True,
) -> ChromeOptions:
    """Makes the Chrome options."""
    opts = ChromeOptions()
    opts.add_argument("--disable-notifications")  # type: ignore[reportUnknownMemberType]
    opts.add_argument("--mute-audio")  # type: ignore[reportUnknownMemberType]

    if headless:
        opts.add_argument("--headless=new")  # type: ignore[reportUnknownMemberType]

    if disable_gpu:
        opts.add_argument("--disable-gpu")  # type: ignore[reportUnknownMemberType]

    if disable_dev_shm_usage:
        opts.add_argument("--disable-dev-shm-usage")  # type: ignore[reportUnknownMemberType]

    if user_agent:
        opts.add_argument(f"--user-agent={user_agent}")  # type: ignore[reportUnknownMemberType]

    if _IS_DOCKER:
        opts.add_argument("--remote-debugging-address=0.0.0.0")  # type: ignore[reportUnknownMemberType]

    return opts


def open_webdriver(  # pylint: disable=too-many-arguments,too-many-branches
    headless: bool = True,
    verbose: bool = False,  # pylint: disable=unused-argument
    timeout: float = INSTALL_TIMEOUT,
    disable_gpu: Optional[bool] = True,
    disable_dev_shm_usage: bool = True,
    user_agent: str | None = None,
) -> Driver:
    """Opens the Chrome web driver."""
    user_agent = user_agent or _user_agent()
    _init_log()

    if headless or FORCE_HEADLESS:
        if FORCE_HEADLESS and not headless:
            print("\n  WARNING: HEADLESS ENVIRONMENT DETECTED, FORCING HEADLESS")
        headless = True

    opts = _make_options(
        headless=headless,
        user_agent=user_agent,
        disable_gpu=disable_gpu if disable_gpu is not None else True,
        disable_dev_shm_usage=disable_dev_shm_usage,
    )

    lock = filelock.FileLock(LOCK_FILE)
    with lock.acquire(timeout=timeout):
        if verbose:
            print("  Launching Chrome WebDriver...")

    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)

        # Use specific chromedriver version
        service = ChromeService(
            ChromeDriverManager(driver_version="130.0.6723.116").install()
        )
        driver = webdriver.Chrome(service=service, options=opts)

        if headless:
            driver.set_window_size(1440, 900)  # type: ignore[reportUnknownMemberType]

        return driver

    except Exception as err:  # pylint: disable=broad-except
        traceback.print_exc()
        log_file_text = ""
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, encoding="utf-8", mode="r") as filed:
                log_file_text = filed.read()
        print(f"{__file__}: Error: {err}")
        print(f"{LOG_FILE}:\n{log_file_text}")
        raise
