# pylint: disable=too-many-arguments

"""Library json module."""


from youtube_sync.library_data import Source

# f"https://www.brighteon.com/channels/{channel_name}"


def to_channel_url(source: Source, channel_name: str) -> str:
    from .rumble.rumble_extra import to_channel_url as to_channel_url_rumble
    from .youtube.youtube import to_channel_url as to_channel_url_youtube

    if source == Source.YOUTUBE:
        return to_channel_url_youtube(channel_name)
    elif source == Source.RUMBLE:
        return to_channel_url_rumble(channel_name)
    elif source == Source.BRIGHTEON:
        return f"https://www.brighteon.com/channels/{channel_name}"
    raise ValueError(f"Unknown source: {source}")
