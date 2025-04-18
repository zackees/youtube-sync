import _thread
import logging
import os
import subprocess
import time
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


def _update_proxies_once() -> None:

    global _PROXIES_UPDATED
    if _PROXIES_UPDATED:
        return
    with _UPDATE_PROXIES_LOCK:
        YtDLPProxy.update()
        _PROXIES_UPDATED = True


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

    _update_proxies_once()

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

    class RealYtdlp:
        def execute(self, cmd_list: list[str], yt_dlp_path: Path | None = None) -> bool:
            full_cmd = [yt_exe.exe.as_posix()] + cmd_list
            # subprocess.run(full_cmd, check=True)
            proc = subprocess.Popen(
                full_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            with proc:
                assert proc.stdout is not None
                for line in proc.stdout:
                    linestr = line.decode("utf-8").strip()
                    print(linestr)
                proc.wait()
                if proc.returncode != 0:
                    logging.error(f"yt-dlp failed with return code {proc.returncode}")
                    return False
                return True

    class RealOrProxy:
        def __init__(self) -> None:
            self.proxy = YtDLPProxy()
            self.real = RealYtdlp()
            self.real_failures = 0

        def execute(self, cmd_list: list[str], yt_dlp_path: Path | None = None) -> bool:
            cmd_str = subprocess.list2cmdline(cmd_list)
            logger.info(f"Executing command:\n  {cmd_str}\n")
            if self.real_failures > 3:
                return self.proxy.execute(cmd_list, yt_dlp_path=yt_exe.exe)
            try:
                self.real.execute(cmd_list, yt_dlp_path=yt_exe.exe)
                return True
            except subprocess.CalledProcessError:
                self.real_failures += 1
                return self.proxy.execute(cmd_list, yt_dlp_path=yt_exe.exe)

        def is_proxy(self) -> bool:
            return self.real_failures > 3

    executor: RealOrProxy = RealOrProxy()

    for attempt in range(retries):
        if check_keyboard_interrupt():
            return KeyboardInterruptException(
                "Download aborted due to previous keyboard interrupt"
            )

        try:
            # cmd_str = subprocess.list2cmdline(cmd_list)
            # logger.debug(
            #     "\n\n###################\n# Running command: %s\n###################\n\n",
            #     cmd_str,
            # )
            ok = executor.execute(cmd_list, yt_dlp_path=yt_exe.exe)
            # proc = subprocess.Popen(cmd_list)
            # while True:
            #     if proc.poll() is not None:
            #         break
            #     if check_keyboard_interrupt():
            #         proc.terminate()
            #         return KeyboardInterruptException(
            #             "Download aborted due to previous keyboard interrupt"
            #         )
            #     time.sleep(0.1)

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
                # if YtDlpCmdRunner.is_keyboard_interrupt(rtn):
                #     set_keyboard_interrupt()
                #     raise KeyboardInterrupt("KeyboardInterrupt")
                # last_error = subprocess.CalledProcessError(
                #     returncode=proc.returncode, cmd=cmd_list
                # )
                logger.info(
                    f"Download attempt {attempt+1}/{retries} failed: {last_error}"
                )
                if executor.is_proxy():
                    logger.error("Refreshing cookies")
                    cookies: Cookies = Cookies.from_browser(source=source, save=True)
                    cookies_txt = Path(cookies.path_txt)
                    if cookies_txt is not None and cookies_txt.exists():
                        cookies_txt_str = cookies_txt.read_text()
                        logger.info(f"Cookies ({cookies_txt}):\n{cookies_txt_str}\n")
                    # update the proxies
                    YtDLPProxy.update()

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
