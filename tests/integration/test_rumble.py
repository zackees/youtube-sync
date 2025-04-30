"""
Command entry point.
"""

from youtube_sync import Source
from youtube_sync.integration_test import Args, integration_test

RUMBLE_PLANDEMIC = Args(
    source=Source.RUMBLE,
    channel_name="PlandemicSeriesOfficial",
    channel_id="PlandemicSeriesOfficial",
    limit_scan=1,
    skip_download=False,
    download_limit=1,
    skip_scan=False,
)

if __name__ == "__main__":
    integration_test(RUMBLE_PLANDEMIC)
