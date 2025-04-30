"""
Command entry point.
"""

from youtube_sync import Source
from youtube_sync.integration_test import Args, integration_test

BRIGHTEON_HHR = Args(
    source=Source.BRIGHTEON,
    channel_name="hrreport",
    channel_id="hrreport",
    limit_scan=1,
    skip_download=False,
    download_limit=1,
    skip_scan=False,
)

if __name__ == "__main__":
    integration_test(BRIGHTEON_HHR)
