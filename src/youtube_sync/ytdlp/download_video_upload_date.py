import logging
import subprocess
from datetime import datetime
from pathlib import Path

from youtube_sync.cookies import Source

from .download_best_audio import RealOrProxyExecutor
from .error import (
    KeyboardInterruptException,
    check_keyboard_interrupt,
)
from .exe import YtDlpCmdRunner

# cookies


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)


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
