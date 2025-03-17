"""
Command entry point.
"""

# pylint: disable=consider-using-f-string

import os
from pathlib import Path

from base import Args, integration_test

from youtube_sync import Source

if __name__ == "__main__":
    args = Args(
        source=Source.RUMBLE,
        channel_name="GGreenwald",
        output=Path(os.path.join(os.getcwd(), "tmp", "@silverguru", "youtube")),
        limit_scroll_pages=1,
        skip_download=False,
        download_limit=1,
        skip_scan=False,
        yt_dlp_uses_docker=False,
    )
    integration_test(args)
