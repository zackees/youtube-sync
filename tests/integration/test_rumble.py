"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


from base import Args, integration_test

from youtube_sync import Source

RUMBLE_GLEN_GRENWALD = Args(
    source=Source.RUMBLE,
    channel_name="GGreenwald",
    limit_scroll_pages=1,
    skip_download=False,
    download_limit=1,
    skip_scan=False,
    yt_dlp_uses_docker=False,
)

if __name__ == "__main__":
    integration_test(RUMBLE_GLEN_GRENWALD)
