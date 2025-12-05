import _thread
import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
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
        self,
        cmd_list: list[str],
        yt_dlp_path: Path | None = None,
        timeout_seconds: int = 1800,
    ) -> ExeResult:
        """Execute a yt-dlp command.

        Args:
            cmd_list: Command arguments to pass to yt-dlp
            yt_dlp_path: Path to the yt-dlp executable
            timeout_seconds: Timeout in seconds (default 30 minutes)

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
        timeout_seconds: int = 1800,  # 30 minutes default
    ) -> ExeResult:
        full_cmd = [self.yt_exe.exe.as_posix()] + cmd_list
        logger.info(f"Executing command:\n  {subprocess.list2cmdline(full_cmd)}\n")
        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # Unbuffered
        )
        stdout_lines: list[str] = []
        last_output_time = time.time()
        text_buffer = ""  # For complete text lines
        byte_buffer = b""  # For incomplete UTF-8 sequences

        with proc:
            assert proc.stdout is not None
            # Read in small chunks and treat both \n and \r as line endings
            while True:
                chunk = proc.stdout.read(1024)
                if not chunk:
                    # End of stream - decode any remaining bytes and save content
                    if byte_buffer:
                        text_buffer += byte_buffer.decode("utf-8", errors="replace")
                    if text_buffer.strip():
                        print(text_buffer, flush=True)
                        stdout_lines.append(text_buffer)
                    break

                # Accumulate bytes
                byte_buffer += chunk
                last_output_time = time.time()

                # Try to decode as much as possible
                # Find the last valid UTF-8 boundary
                decoded_text = ""
                for i in range(len(byte_buffer), max(0, len(byte_buffer) - 3), -1):
                    # Try to decode up to position i
                    try:
                        decoded_text = byte_buffer[:i].decode("utf-8")
                        # Success - keep any remaining bytes for next iteration
                        byte_buffer = byte_buffer[i:]
                        break
                    except UnicodeDecodeError:
                        # Continue trying with fewer bytes
                        continue

                text_buffer += decoded_text

                # Process complete lines (split on both \n and \r)
                while "\n" in text_buffer or "\r" in text_buffer:
                    # Find the earliest line ending
                    newline_pos = text_buffer.find("\n")
                    cr_pos = text_buffer.find("\r")

                    if newline_pos == -1:
                        line_end_pos = cr_pos
                    elif cr_pos == -1:
                        line_end_pos = newline_pos
                    else:
                        line_end_pos = min(newline_pos, cr_pos)

                    line = text_buffer[:line_end_pos]
                    text_buffer = text_buffer[line_end_pos + 1 :]

                    # Print and save all non-empty lines
                    if line:
                        print(line, flush=True)
                        stdout_lines.append(line)

                # Check timeout
                if time.time() - last_output_time > timeout_seconds:
                    proc.kill()
                    logging.error(f"yt-dlp timed out after {timeout_seconds} seconds")
                    return ExeResult(
                        ok=False,
                        stdout="\n".join(stdout_lines) + "\n",
                        stderr=None,
                        error=f"yt-dlp timed out after {timeout_seconds} seconds",
                    )

            stdout = "\n".join(stdout_lines) + "\n"
            proc.wait()
            if proc.returncode != 0:
                logging.error(f"yt-dlp failed with return code {proc.returncode}")
                return ExeResult(
                    ok=False,
                    stdout=stdout,
                    stderr=None,
                    error=f"yt-dlp failed with return code {proc.returncode}",
                )
        logger.info(f"yt-dlp command succeeded: {full_cmd}")
        return ExeResult(ok=True, stdout=stdout, stderr=None)

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
        self,
        cmd_list: list[str],
        yt_dlp_path: Path | None = None,
        timeout_seconds: int = 1800,
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
            return self.real.execute(
                cmd_list, yt_dlp_path=self.yt_exe.exe, timeout_seconds=timeout_seconds
            )
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

    # For Rumble, the audio format has extension "audio" which yt-dlp rejects
    # So we download the smallest video format instead (360p) and extract audio
    format_selector = "mp4-360p/worst" if source == Source.RUMBLE else "bestaudio/worst"

    # Command to download best audio format without any conversion
    cmd_list = [
        # yt_dlp_proxy_path.as_posix(),
        url,
        "--user-agent",
        user_agent,
        "-f",
        format_selector,  # Select best audio format
        "--no-playlist",  # Don't download playlists
        "--output",
        f"{temp_file.as_posix()}.%(ext)s",  # Output filename pattern
        "--progress",  # Show progress even when stdout is not a TTY
    ]

    if no_geo_bypass:
        cmd_list.append("--no-geo-bypass")

    if cookies_txt is not None:
        cmd_list.extend(["--cookies", cookies_txt.as_posix()])

    # Add browser impersonation for Rumble to bypass anti-bot protection
    if source == Source.RUMBLE:
        cmd_list.extend(["--impersonate", "chrome-120", "--legacy-server-connect"])

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
