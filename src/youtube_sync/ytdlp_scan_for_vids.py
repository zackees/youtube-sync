# pylint: disable=too-many-locals

"""
Scrapes the brighteon website for video urls and downloads them.
"""

import logging
import subprocess
import warnings
from pathlib import Path

from youtube_sync import json_util
from youtube_sync.library import VidEntry

# Set up module logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def _json_to_vid_entry(data: dict) -> VidEntry:
    """Create a VidEntry from a dictionary."""
    title = data["title"]
    url = data["webpage_url"]
    return VidEntry(title=title, url=url, data=data)


def scan_for_vids(
    channel_url: str,
    stored_vids: list[VidEntry],
    limit: int | None,
    cookies_txt: Path | None,
    full_scan: bool | None = None,
) -> list[VidEntry]:
    """Scan for videos on the channel."""
    if limit is not None and limit < 0:
        limit = None

    if full_scan:
        limit = None

    stored_vids_set: set[VidEntry] = set(stored_vids)

    cmd_list: list[str] = [
        "yt-dlp",
        "--skip-download",
        "--print-json",
    ]

    # Add cookies file if provided
    if cookies_txt is not None:
        cmd_list += ["--cookies", str(cookies_txt)]

    if limit is not None:
        cmd_list += ["--playlist-end", str(limit)]
    cmd_list += [channel_url]
    cmd_str = subprocess.list2cmdline(cmd_list)
    logger.debug(
        "\n\n###################\n# Running command: %s\n###################\n\n",
        cmd_str,
    )
    popen = subprocess.Popen(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # grab the stdout pipe
    stdout = popen.stdout
    assert stdout is not None
    # read the output
    out: list[VidEntry] = []
    killed = False

    def kill() -> None:
        """Kill the process."""
        nonlocal killed
        if not killed:
            popen.kill()
            killed = True

    vid: VidEntry | None = None
    for line_bytes in stdout:
        line: str | None = None
        try:
            line = line_bytes.decode("utf-8")
            data = json_util.load_dict(line)
            vid = _json_to_vid_entry(data)
        except Exception as e:
            if isinstance(line, str):
                logger.error("Error parsing line: %s", line)
            logger.error("Error: %s", e)
            continue
        assert isinstance(vid, VidEntry)
        logger.debug("Parsed video: %s", vid)
        # print(vid)
        logger.debug(vid)
        if vid in stored_vids_set:
            logger.debug(
                f"Breaking out of loop because {vid} is already in the library"
            )
            kill()
            break
        out.append(vid)
    # wait for the process to finish
    popen.wait()
    # check the return code
    rtn = popen.returncode
    if rtn != 0:
        # is this a keyboard exception from the subprocess?
        if rtn < 0 or rtn > 1000:  # win32 is much higher than 1000
            raise KeyboardInterrupt(f"yt-dlp failed with return code {rtn}")
        else:
            if not killed:
                warnings.warn(f"error on yt-dlp failed with return code {rtn}")
    return out


def unit_test(limit=1) -> int:
    """Run the tests."""
    # change logging level to debug
    logger.setLevel(logging.DEBUG)
    vids = scan_for_vids(
        channel_url="https://www.brighteon.com/channels/hrreport",
        stored_vids=[],
        limit=limit,
        cookies_txt=None,
    )
    print(vids)
    logger.info("Unit test completed")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(unit_test())
