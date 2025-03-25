"""
Command entry point.
"""

from base import Args, integration_test

from youtube_sync import Source

BRIGHTEON_HHR = Args(
    source=Source.BRIGHTEON,
    channel_name="hrreport",
    limit_scan=1,
    skip_download=False,
    download_limit=1,
    skip_scan=False,
)

if __name__ == "__main__":
    integration_test(BRIGHTEON_HHR)
