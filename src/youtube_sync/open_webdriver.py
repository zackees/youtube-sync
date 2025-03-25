import os
import sys
import traceback
from typing import Optional

import filelock  # type: ignore
from open_webdriver.path import LOG_FILE, WDM_DIR
from selenium import webdriver
from selenium.webdriver import FirefoxOptions  # type: ignore
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.remote.webdriver import WebDriver as Driver  # type: ignore

INSTALL_TIMEOUT = float(60 * 10)  # Up to 10 minutes of install time.
FORCE_HEADLESS = sys.platform == "linux" and "DISPLAY" not in os.environ

os.makedirs(WDM_DIR, exist_ok=True)
LOCK_FILE = os.path.join(WDM_DIR, "lock.file")


def _user_agent(firefox_version: str | None = None) -> str:
    """Gets the user agent."""
    firefox_version = firefox_version or "122.0"
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:"
        f"{firefox_version}) Gecko/20100101 Firefox/{firefox_version}"
    )


def _init_log() -> None:
    """Initializes the log."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, encoding="utf-8", mode="w") as filed:
        filed.write(f"{__file__}: Starting up web driver.\n")
        if sys.platform == "linux":
            if os.geteuid() == 0:
                filed.write("\n\n  WARNING: Running as root. The driver may crash!\n\n")


def _make_options(
    headless: bool,
    user_agent: str | None,
) -> FirefoxOptions:
    """Makes the Firefox options."""
    opts: FirefoxOptions = FirefoxOptions()
    opts.set_preference("dom.webnotifications.enabled", False)
    opts.set_preference("media.volume_scale", "0.0")

    if headless:
        opts.add_argument("--headless")

    if user_agent:
        opts.set_preference("general.useragent.override", user_agent)

    return opts


def open_webdriver(  # pylint: disable=too-many-arguments,too-many-branches
    headless: bool = True,
    verbose: bool = False,  # pylint: disable=unused-argument
    timeout: float = INSTALL_TIMEOUT,
    disable_gpu: Optional[bool] = None,  # unused for Firefox
    disable_dev_shm_usage: bool = True,  # unused for Firefox
    user_agent: str | None = None,
) -> Driver:
    """Opens the Firefox web driver."""
    user_agent = user_agent or _user_agent()
    _init_log()

    if headless or FORCE_HEADLESS:
        if FORCE_HEADLESS and not headless:
            print("\n  WARNING: HEADLESS ENVIRONMENT DETECTED, FORCING HEADLESS")
        headless = True

    opts = _make_options(headless=headless, user_agent=user_agent)

    lock = filelock.FileLock(LOCK_FILE)
    with lock.acquire(timeout=timeout):
        if verbose:
            print("  Launching Firefox WebDriver...")

    try:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)

        service = FirefoxService()  # Assumes geckodriver is in PATH
        driver = webdriver.Firefox(service=service, options=opts)

        if headless:
            driver.set_window_size(1440, 900)

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
