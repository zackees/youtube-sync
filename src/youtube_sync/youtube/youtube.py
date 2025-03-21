"""
Command entry point.
"""

# pylint: disable=consider-using-f-string


def to_channel_url(channel: str) -> str:
    """Convert channel name to channel URL."""
    out = f"https://www.youtube.com/{channel}/videos"
    return out
