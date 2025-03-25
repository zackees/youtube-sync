import logging
from pathlib import Path

from youtube_sync.cli.sync_multiple import Args, run

# set the root logger to debug
logging.getLogger().setLevel(logging.DEBUG)
# filter out filelock debug messages
logging.getLogger("filelock").setLevel(logging.INFO)


def main() -> None:
    """Main function."""
    args = Args(
        config=Path("config.json"),
        dry_run=False,
    )

    run(args)


if __name__ == "__main__":
    main()
