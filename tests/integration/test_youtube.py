"""
Command entry point.
"""

from base import Args, integration_test

from youtube_sync import Source

YOURTUBE_SILVER_GURU = Args(
    source=Source.YOUTUBE,
    channel_name="silverguru",
    channel_id="@silverguru",
    limit_scan=1,
    skip_download=False,
    download_limit=1,
    skip_scan=False,
)

if __name__ == "__main__":
    integration_test(YOURTUBE_SILVER_GURU)
