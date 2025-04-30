from dataclasses import dataclass

# cookies


@dataclass
class ExeResult:
    """Class to hold the result of a yt-dlp command."""

    ok: bool
    output: str | None
    error: str | None = None
