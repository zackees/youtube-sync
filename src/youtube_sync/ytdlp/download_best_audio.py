import _thread
import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from filelock import FileLock
from yt_dlp_proxy import YtDLPProxy

from youtube_sync.cookies import Cookies, Source

from .error import (
    KeyboardInterruptException,
    check_keyboard_interrupt,
    set_keyboard_interrupt,
)
from .exe import YtDlpCmdRunner

# cookies


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)


_UPDATE_PROXIES_LOCK = FileLock("proxies.lock")
_PROXIES_UPDATED = False

_DOWNLOADER_COUNTER = 0
_STARTUP_TIME = time.time()


@dataclass
class ExeResult:
    """Class to hold the result of a yt-dlp command."""

    ok: bool
    stdout: str | None
    stderr: str | None
    error: str | None = None


def _update_proxies_once() -> None:
    """Legacy function kept for compatibility."""
    global _PROXIES_UPDATED
    if _PROXIES_UPDATED:
        return
    with _UPDATE_PROXIES_LOCK:
        YtDLPProxy.update()
        _PROXIES_UPDATED = True


class YtDlpExecutor(ABC):
    """Abstract base class for yt-dlp execution strategies."""

    @abstractmethod
    def execute(
        self, cmd_list: list[str], yt_dlp_path: Path | None = None
    ) -> ExeResult:
        """Execute a yt-dlp command.

        Args:
            cmd_list: Command arguments to pass to yt-dlp
            yt_dlp_path: Path to the yt-dlp executable

        Returns:
            True if execution was successful, False otherwise
        """
        pass

    @abstractmethod
    def is_proxy(self) -> bool:
        """Check if this executor is using a proxy.

        Returns:
            True if using proxy, False otherwise
        """
        pass


class RealYtdlp(YtDlpExecutor):
    """Execute yt-dlp directly as a subprocess."""

    def __init__(self, yt_exe: YtDlpCmdRunner):
        self.yt_exe = yt_exe

    def execute(
        self,
        cmd_list: list[str],
        yt_dlp_path: Path | None = None,
    ) -> ExeResult:
        full_cmd = [self.yt_exe.exe.as_posix()] + cmd_list
        logger.info(f"Executing command:\n  {subprocess.list2cmdline(full_cmd)}\n")
        proc = subprocess.Popen(
            full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        with proc:
            assert proc.stdout is not None
            assert proc.stderr is not None
            for line in proc.stdout:
                linestr = line.decode("utf-8").strip()
                print(linestr)
                stdout_lines.append(linestr)
            stdout = "\n".join(stdout_lines) + "\n"

            for line in proc.stderr:
                linestr = line.decode("utf-8").strip()
                print(linestr)
                stderr_lines.append(linestr)
            stderr = "\n".join(stderr_lines) + "\n"
            proc.wait()
            if proc.returncode != 0:
                logging.error(f"yt-dlp failed with return code {proc.returncode}")
                return ExeResult(
                    ok=False,
                    stdout=stdout,
                    stderr=stderr,
                    error=f"yt-dlp failed with return code {proc.returncode}",
                )
        logger.info(f"yt-dlp command succeeded: {full_cmd}")
        return ExeResult(ok=True, stdout=stdout, stderr=stderr)

    def is_proxy(self) -> bool:
        return False


class RealOrProxyExecutor(YtDlpExecutor):
    """Executor that tries real execution first, then falls back to proxy if needed."""

    def __init__(self, yt_exe: YtDlpCmdRunner, source: Source):
        self.proxy = YtDLPProxy()
        self.real = RealYtdlp(yt_exe)
        self.real_failures = 0
        self.yt_exe = yt_exe
        self.source = source
        # Update proxies once during initialization
        # self._update_proxies()

    def _update_proxies(self) -> None:
        """Update proxies once."""
        global _PROXIES_UPDATED
        if not _PROXIES_UPDATED:
            with _UPDATE_PROXIES_LOCK:
                YtDLPProxy.update()
                _PROXIES_UPDATED = True

    def _refresh_cookies(self, source: Source) -> Path | None:
        """Refresh cookies and return the path to the cookies file."""
        if source is None:
            logger.warning("Cannot refresh cookies: source is None")
            return None

        logger.info("Refreshing cookies")
        cookies: Cookies = Cookies.from_browser(source=source, save=True)
        cookies_txt = Path(cookies.path_txt)
        if cookies_txt is not None and cookies_txt.exists():
            cookies_txt_str = cookies_txt.read_text()
            logger.info(f"Cookies ({cookies_txt}):\n{cookies_txt_str}\n")
        return cookies_txt

    def execute(
        self, cmd_list: list[str], yt_dlp_path: Path | None = None
    ) -> ExeResult:
        # Always ensure proxies are updated

        if self.real_failures > 3:
            self._update_proxies()
            ok: bool = self.proxy.execute(cmd_list, yt_dlp_path=self.yt_exe.exe)
            out: ExeResult = ExeResult(
                ok=ok,
                stdout="NO OUTPUT FOR PROXY",
                stderr="NO STDERR FOR PROXY",
                error="ERROR HAPPENED" if not ok else None,
            )
            return out
        try:
            return self.real.execute(cmd_list, yt_dlp_path=self.yt_exe.exe)
        except subprocess.CalledProcessError:
            self.real_failures += 1
            # If we're switching to proxy mode, refresh cookies and proxies
            if self.real_failures > 3 and self.source is not None:
                self._refresh_cookies(self.source)
                self._update_proxies()
            ok: bool = self.proxy.execute(cmd_list, yt_dlp_path=self.yt_exe.exe)
            out: ExeResult = ExeResult(
                ok=ok,
                stdout="NO OUTPUT FOR PROXY",
                stderr="NO STDERR FOR PROXY",
                error="ERROR HAPPENED" if not ok else None,
            )
            return out

    def is_proxy(self) -> bool:
        return self.real_failures > 3


def yt_dlp_get_upload_date(
    yt_exe: YtDlpCmdRunner,
    source: Source,
    url: str,
    cookies_txt: Path | None,
    no_geo_bypass: bool = True,
) -> datetime | Exception:
    """Get the upload date of a video.

    Args:
        yt_exe: YtDlpCmdRunner instance
        source: Source platform (YouTube, etc.)
        url: The URL of the video
        cookies_txt: Path to cookies.txt file or None
        no_geo_bypass: Whether to disable geo-bypass

    Returns:
        datetime object representing the upload date or Exception if failed
    """
    from datetime import datetime

    from youtube_sync.cookies import get_user_agent

    if check_keyboard_interrupt():
        return KeyboardInterruptException(
            "Operation aborted due to previous keyboard interrupt"
        )

    user_agent: str = get_user_agent()

    # Command to get video info in JSON format
    cmd_list = [
        url,
        "--user-agent",
        user_agent,
        "--no-playlist",
        "--print",
        "%(upload_date)s",
        "--skip-download",
    ]

    if no_geo_bypass:
        cmd_list.append("--no-geo-bypass")

    if cookies_txt is not None:
        cmd_list.extend(["--cookies", cookies_txt.as_posix()])

    try:
        # Create an executor that will handle proxies and cookies automatically
        executor = RealOrProxyExecutor(yt_exe, source=source)

        # Use the executor to run the command
        rslt = executor.execute(cmd_list, yt_dlp_path=yt_exe.exe)
        if not rslt.ok:
            return RuntimeError("Failed to get upload date")

        logger.info(f"Command stdout: {rslt.stdout}")
        logger.info(f"Command stderr: {rslt.stderr}")

        # yt-dlp returns upload date in format YYYYMMDD
        upload_date_str = rslt.stdout.strip() if rslt.stdout else ""

        if not upload_date_str:
            return ValueError(f"Invalid upload date format: {upload_date_str}")

        # Parse the date string into a datetime object
        upload_date = datetime.strptime(upload_date_str, "%Y%m%d")
        return upload_date

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get upload date: {e}")
        return e
    except Exception as e:
        logger.error(f"Error getting upload date: {e}")
        return e


def yt_dlp_download_best_audio(
    yt_exe: YtDlpCmdRunner,
    source: Source,
    url: str,
    temp_dir: Path,
    cookies_txt: Path | None,
    no_geo_bypass: bool = True,
    retries: int = 1,
) -> Path | Exception:
    from youtube_sync.cookies import get_user_agent

    """Download the best audio from a URL to a temporary directory without conversion.

    Args:
        url: The URL to download from
        temp_dir: Directory to save the temporary file
        cookies_txt: Path to cookies.txt file or None
        yt_exe: Path to yt-dlp executable or None to auto-detect
        no_geo_bypass: Whether to disable geo-bypass
        retries: Number of download attempts to make before giving up

    Returns:
        Path to the downloaded audio file or Exception if download failed
    """
    if check_keyboard_interrupt():
        return KeyboardInterruptException(
            "Download aborted due to previous keyboard interrupt"
        )

    # Use a generic name for the temporary file - let yt-dlp determine the extension
    temp_file = Path(os.path.join(temp_dir, "temp_audio"))

    user_agent: str = get_user_agent()

    # Command to download best audio format without any conversion
    cmd_list = [
        # yt_dlp_proxy_path.as_posix(),
        url,
        "--user-agent",
        user_agent,
        "-f",
        "bestaudio/worst",  # Select best audio format
        "--no-playlist",  # Don't download playlists
        "--output",
        f"{temp_file.as_posix()}.%(ext)s",  # Output filename pattern
    ]

    if no_geo_bypass:
        cmd_list.append("--no-geo-bypass")

    if cookies_txt is not None:
        cmd_list.extend(["--cookies", cookies_txt.as_posix()])

    ke: KeyboardInterrupt | None = None
    last_error: Exception | None = None

    executor: YtDlpExecutor = RealOrProxyExecutor(yt_exe, source=source)

    for attempt in range(retries):
        if check_keyboard_interrupt():
            return KeyboardInterruptException(
                "Download aborted due to previous keyboard interrupt"
            )

        try:
            # Execute the command
            ok = executor.execute(cmd_list, yt_dlp_path=yt_exe.exe)
            if ok:
                # Find the downloaded file (with whatever extension yt-dlp used)
                downloaded_files = list(temp_dir.glob("temp_audio.*"))
                if not downloaded_files:
                    last_error = FileNotFoundError(
                        f"No audio file was downloaded to {temp_dir}"
                    )
                    continue
                global _DOWNLOADER_COUNTER
                _DOWNLOADER_COUNTER += 1
                running_time_seconds = time.time() - _STARTUP_TIME
                running_time_hours = running_time_seconds / 3600
                logger.info(
                    f"\n###################################################################\n"
                    f"# Downloaded {_DOWNLOADER_COUNTER} file(s)\n"
                    f"# Downloaded {downloaded_files[0]} in {running_time_hours:.1f} hours\n"
                    f"###################################################################\n"
                )
                return downloaded_files[0]
            else:
                logger.info(
                    f"Download attempt {attempt+1}/{retries} failed: {last_error}"
                )

        except KeyboardInterrupt as kee:
            set_keyboard_interrupt()
            _thread.interrupt_main()
            ke = kee
            break
        except Exception as e:
            last_error = e
            print(f"Download attempt {attempt+1}/{retries} failed: {e}")

    if ke is not None:
        raise ke

    return last_error or RuntimeError(
        f"Failed to download {url} after {retries} attempts"
    )
