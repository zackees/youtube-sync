import logging
from pathlib import Path

from youtube_sync.cli.sync_multiple import Args, run

# set debug
logging.basicConfig(level=logging.DEBUG)


def main() -> None:
    """Main function."""
    args = Args(
        config=Path("config.json"),
        dry_run=False,
    )

    run(args)


if __name__ == "__main__":
    main()
