# pylint: disable=too-many-locals

"""
Scrapes the brighteon website for video urls and downloads them.
"""

import _thread
import argparse
import logging
import os
import subprocess
import sys
import warnings
from pathlib import Path

from playwright.sync_api import Page

from youtube_sync import json_util
from youtube_sync.library import Library, VidEntry
from youtube_sync.library_data import Source
from youtube_sync.playwright_launcher import launch_playwright, set_headless

BASE_URL = "https://www.brighteon.com"

INSTALLED = False

# Set up module logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.FATAL)


def _fetch_vid_infos(page: Page, channel_url: str, page_num: int) -> list[VidEntry]:
    """Get the urls from a channel page. Throws exception when page not found."""
    last_exception: BaseException | None = None
    logger.debug("Starting _fetch_vid_infos for page %d of %s", page_num, channel_url)

    for attempt in range(10):
        try:
            # From: https://www.brighteon.com/channels/hrreport
            # To: https://www.brighteon.com/channels/hrreport/videos?page=1
            url = f"{channel_url}/videos?page={page_num}"
            logger.info(f"Fetching video list from {url}")
            logger.debug(f"Attempt {attempt+1}/10 to fetch {url}")

            response = page.goto(url)
            logger.debug(f"Got response object: {response}")

            assert response
            if response.status != 200:
                msg = f"Failed to fetch {url}, status: {response.status}"
                logger.warning(msg)
                warnings.warn(msg)
                raise ValueError(msg)

            # get all div class="post" objects
            logger.debug("Querying for div.post elements")
            posts = page.query_selector_all("div.post")
            logger.debug(f"Found {len(posts)} post elements")

            # get the first one
            vids: list[VidEntry] = []
            for i, post in enumerate(posts):
                try:
                    logger.debug(f"Processing post {i+1}/{len(posts)}")
                    link = post.query_selector("a")
                    logger.debug(f"Found link element: {link}")
                    assert link

                    href = link.get_attribute("href")
                    logger.debug(f"Raw href: {href}")
                    assert href

                    title = post.query_selector("div.title")
                    logger.debug(f"Found title element: {title}")
                    assert title

                    title_text = title.inner_text().strip()
                    logger.debug(f"Title text: {title_text}")

                    href = BASE_URL + href
                    logger.debug(f"Full URL: {href}")

                    vids.append(VidEntry(title=title_text, url=href))
                    logger.debug(f"Added video entry: {title_text} - {href}")
                except Exception as e:  # pylint: disable=broad-except
                    logger.error(f"Failed to process post {i+1}: {e}", exc_info=True)
                    warnings.warn(f"Failed to get url: {e}")

            logger.info(f"Found {len(vids)} videos on page {page_num}")
            print(f"Found {len(vids)} videos.")
            return vids

        except KeyboardInterrupt:
            logger.critical("Keyboard interrupt detected, exiting")
            _thread.interrupt_main()
            raise
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"Attempt {attempt+1} failed: {e}", exc_info=True)
            print(f"Attempt to fetch video info failed with error: {e}. Retrying...")
            last_exception = e

    assert last_exception is not None
    logger.critical(f"All attempts failed for page {page_num}: {last_exception}")
    raise last_exception


def _scan_for_vids(
    channel_url: str,
    full_scan: bool,
    stored_vids: list[VidEntry],
    limit: int = -1,
) -> list[VidEntry]:
    """Simple test to verify the title of a page."""
    logger.info(f"Starting scan for videos from {channel_url}")
    logger.debug(
        f"Full scan: {full_scan}, Limit: {limit}, Stored videos: {len(stored_vids)}"
    )

    count = 0
    with launch_playwright(timeout_seconds=300) as (page, _):
        # Determine whether to run headless based on the environment variable
        urls: list[VidEntry] = []
        page_num = 0
        while True:
            if limit > -1:
                if count >= limit:
                    logger.info(f"Reached scan limit of {limit} pages")
                    break
            count += 1
            try:
                logger.info(f"Scanning page {page_num}")
                new_urls: list[VidEntry] = _fetch_vid_infos(page, channel_url, page_num)
                set_new_urls = set(new_urls)
                set_stored_vids = set(stored_vids)

                # if the new urls are fully contained in the stored vids, then we are done
                if not full_scan and (set_new_urls <= set_stored_vids):
                    logger.info("All new videos already in library, halting scan")
                    warnings.warn(
                        "All the new videos are already in the library... halting scan."
                    )
                    break

                page_num += 1
                urls += new_urls
                logger.debug(f"Total videos found so far: {len(urls)}")

            except Exception as e:  # pylint: disable=broad-except
                logger.error(
                    f"Failed to get URLs from page {page_num}: {e}", exc_info=True
                )
                warnings.warn(f"Failed to get urls: {e}")
                break

    logger.info(f"Scan complete. Found {len(urls)} videos in total")
    return urls


def _update_library(
    outdir: str, channel_name: str, full_scan: bool, limit: int = -1
) -> Library:
    """Simple test to verify the title of a page."""
    logger.info(f"Updating library for channel {channel_name}")

    channel_url = f"https://www.brighteon.com/channels/{channel_name}"
    library_json = os.path.join(outdir, "library.json")
    logger.debug(f"Channel URL: {channel_url}, Library JSON: {library_json}")

    library: Library = Library.get_or_create(
        channel_name=channel_name,
        channel_url=channel_url,
        source=Source.BRIGHTEON,
        media_output=Path(outdir),
        library_path=Path(library_json),
    )

    stored_vids = library.load()
    logger.debug(f"Loaded {len(stored_vids)} videos from existing library")

    vids = scan_for_vids(
        channel_url=channel_url,
        stored_vids=stored_vids,
        full_scan=full_scan,
        limit=limit,
    )

    logger.info(f"Got {len(vids)} URLs from scan")
    print(f"Got {len(vids)} urls.")
    library.merge(vids, save=True)
    logger.info("Library updated and saved")

    return library


def _json_to_vid_entry(data: dict) -> VidEntry:
    """Create a VidEntry from a dictionary."""
    title = data["title"]
    url = data["webpage_url"]
    return VidEntry(title=title, url=url)


def scan_for_vids(
    channel_url: str,
    stored_vids: list[VidEntry],
    full_scan: bool,
    limit: int | None,
) -> list[VidEntry]:
    """Scan for videos on the channel."""
    if limit is not None and limit < 0:
        limit = None
    if False:
        return _scan_for_vids(channel_url, full_scan, stored_vids, limit)
    else:
        # use yt-dlp --skip-download --playlist-end 1 --print-json https://www.brighteon.com/channels/hrreport
        # to do the scanning instead.
        # We are moving away from playwright because web scrapping sucks.
        cmd_list: list[str] = [
            "yt-dlp",
            "--skip-download",
            "--print-json",
        ]
        if limit is not None:
            cmd_list += ["--playlist-end", str(limit)]
        cmd_list += [channel_url]
        popen = subprocess.Popen(
            cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        # grab the stdout pipe
        stdout = popen.stdout
        assert stdout is not None
        # read the output
        out: list[VidEntry] = []
        for line_bytes in stdout:
            # print(line)
            line = line_bytes.decode("utf-8")
            data = json_util.load_dict(line)
            # data_str = json_dump(data)
            # print(data_str)

            vid: VidEntry = _json_to_vid_entry(data)
            print(vid)
            out.append(vid)
        # wait for the process to finish
        popen.wait()
        # check the return code
        rtn = popen.returncode
        if rtn != 0:
            # is this a keyboard exception from the subprocess?
            if rtn < 0 or rtn > 1000:  # win32 is much higher than 1000
                raise KeyboardInterrupt(f"yt-dlp failed with return code {rtn}")

        return out


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--channel-name",
        type=str,
        help="URL slug of the channel, example: hrreport",
        required=True,
    )
    parser.add_argument("--output", type=str, help="Output directory", required=True)
    parser.add_argument(
        "--limit-downloads",
        type=int,
        default=-1,
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
    )
    parser.add_argument(
        "--yt-dlp-uses-docker",
        action="store_true",
        help="Use docker to run yt-dlp",
    )
    # Add verbosity argument
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (can be used multiple times)",
    )
    set_headless(True)
    # full-scan
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="Scan the entire channel, not just the new videos.",
    )
    args = parser.parse_args()

    # Configure logging based on verbosity level
    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Starting Brighteon bot")
    logger.debug(f"Arguments: {args}")

    if args.yt_dlp_uses_docker:
        os.environ["USE_DOCKER_YT_DLP"] = "1"

    outdir = args.output
    channel = args.channel_name
    download_limit = args.limit_downloads
    skip_download = args.skip_download
    full_scan = args.full_scan
    yt_uses_docker = args.yt_dlp_uses_docker

    library = _update_library(
        outdir, channel, full_scan=full_scan, limit=download_limit
    )

    if not skip_download:
        logger.info("Starting download of missing videos")
        library.download_missing(download_limit, yt_uses_docker)
    else:
        logger.info("Skipping download as requested")

    logger.info("Brighteon bot completed successfully")
    return 0


def unit_test(limit=-1) -> int:
    """Run the tests."""
    # Set up basic logging for unit tests
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting unit test")

    sys.argv.append("--channel-name")
    sys.argv.append("hrreport")
    sys.argv.append("--output")
    sys.argv.append("tmp2")
    # sys.argv.append("--yt-dlp-uses-docker")
    sys.argv.append("--limit-downloads")
    sys.argv.append(str(limit))
    sys.argv.append("-v")  # Add verbosity for testing

    main()
    logger.info("Unit test completed")
    return 0


if __name__ == "__main__":
    sys.exit(unit_test(20))
