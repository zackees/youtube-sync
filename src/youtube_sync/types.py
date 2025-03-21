from enum import Enum


class VideoId(str):
    pass


class ChannelId(str):
    pass


class ChannelName(str):
    pass


class ChannelUrl(str):
    pass


class Source(Enum):
    """Source enum."""

    YOUTUBE = "youtube"
    RUMBLE = "rumble"
    BRIGHTEON = "brighteon"

    @staticmethod
    def from_str(value: str) -> "Source":
        """Convert from string."""
        value = value.lower()
        if value == "youtube":
            return Source.YOUTUBE
        if value == "rumble":
            return Source.RUMBLE
        if value == "brighteon":
            return Source.BRIGHTEON
        raise ValueError(f"Unknown source: {value}")

    @staticmethod
    def check(value: "str | Source") -> bool:
        """Check if value is a Source."""
        if isinstance(value, Source):
            return True
        try:
            _ = Source.from_str(value)
            return True
        except ValueError:
            return False
