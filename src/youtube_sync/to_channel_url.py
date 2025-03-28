# pylint: disable=too-many-arguments

"""Library json module."""


from youtube_sync.fetch_html import fetch_html_using_curl as fetch_html
from youtube_sync.library_data import Source


def to_channel_url(source: Source, channel_id: str) -> str:
    if source == Source.YOUTUBE:
        return _to_channel_url_youtube(channel_id)
    elif source == Source.RUMBLE:
        return _to_channel_url_rumble(channel_id)
    elif source == Source.BRIGHTEON:
        return f"https://www.brighteon.com/channels/{channel_id}"
    raise ValueError(f"Unknown source: {source}")


def _to_channel_url_youtube(channel: str) -> str:
    """Convert channel name to channel URL."""
    out = f"https://www.youtube.com/{channel}/videos"
    return out


def _get_channel_url_for_page(
    channel: str, page_num: int, is_user_channel: bool
) -> str:
    if is_user_channel:
        base_url = f"https://rumble.com/user/{channel}"
    else:
        base_url = f"https://rumble.com/c/{channel}"
    if page_num > 1:
        return f"{base_url}?page={page_num}"
    return base_url


def _to_channel_url_rumble(channel: str) -> str:
    test_url = _get_channel_url_for_page(
        channel=channel, page_num=1, is_user_channel=False
    )
    fetch_response = fetch_html(test_url)
    if fetch_response.ok:
        return test_url
    test_url = _get_channel_url_for_page(
        channel=channel, page_num=1, is_user_channel=True
    )
    fetch_response = fetch_html(test_url)
    if fetch_response.ok:
        return test_url
    raise ValueError(f"Could not find channel or user {channel}")
