import _thread
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from youtube_sync import FSPath
from youtube_sync.pools import FFMPEG_EXECUTORS, FUTURE_RESOLVER_POOL
from youtube_sync.ytdlp.downloader import YtDlpDownloader
from youtube_sync.ytdlp.error import (
    KeyboardInterruptException,
    check_keyboard_interrupt,
    set_keyboard_interrupt,
)
from youtube_sync.ytdlp.ytdlp import Cookies, Source


def _process_conversion(
    downloader: YtDlpDownloader,
) -> tuple[str, FSPath, Exception | None]:
    """Process conversion and copying for a downloaded file.

    Args:
        downloader: The YtDlpDownloader instance with a downloaded file

    Returns:
        Tuple of (url, output_path, exception_or_none)
    """
    try:
        # Convert to MP3
        convert_result = downloader.convert_to_mp3()
        if isinstance(convert_result, Exception):
            return (downloader.url, downloader.outmp3, convert_result)

        # Copy to destination
        downloader.copy_to_destination()
        return (downloader.url, downloader.outmp3, None)
    except Exception as e:
        return (downloader.url, downloader.outmp3, e)
    finally:
        # Clean up resources
        downloader.dispose()


def download_mp3s(
    downloads: list[tuple[str, FSPath]],
    download_pool: ThreadPoolExecutor,
    source: Source,
    cookies: Cookies | None = None,
) -> list[Future[tuple[str, FSPath, Exception | None]]]:
    """Download multiple YouTube videos as MP3s using thread pools.

    Args:
        downloads: List of tuples containing (url, output_path)
        download_pool: Thread pool for downloads
        convert_pool: Thread pool for conversions

    Returns:
        List of futures that will resolve to tuples of (url, output_path, exception_or_none)
        where exception_or_none is None if download was successful,
        or the exception that occurred during download
    """
    result_futures: list[Future[tuple[str, FSPath, Exception | None]]] = []

    # Process each download
    for i, (url, outmp3) in enumerate(downloads):

        result_future: Future[tuple[str, FSPath, Exception | None]] = Future()

        # Extract cookies if needed
        # cookies = self._extract_cookies_if_needed()
        if cookies is not None:
            cookies.refresh()

        cookied_path: Path | None = (
            Path(cookies.path_txt) if cookies is not None else None
        )

        # Submit the entire download and conversion process as a single task
        fut = FUTURE_RESOLVER_POOL.submit(
            _process_download_and_convert,
            url,
            outmp3,
            cookied_path,
            source,
            download_pool,
            result_future,
        )

        # Create a future that will represent the final result for this download
        def on_done_task(count=i) -> None:
            print(
                f"\n###########################\n# Download {count+1}/{len(downloads)} complete\n###########################\n"
            )

        result_futures.append(result_future)
        fut.add_done_callback(lambda _: on_done_task)

    return result_futures


def _process_download_and_convert(
    url: str,
    outmp3: FSPath,
    cookies: Path | None,
    source: Source,
    download_pool: ThreadPoolExecutor,
    result_future: Future[tuple[str, FSPath, Exception | None]],
) -> None:
    """Process the download and conversion for a single URL.

    Args:
        url: The URL to download
        outmp3: Path to save the final MP3 file
        cookies: Path to cookies file or None
        download_pool: Thread pool for downloads
        convert_pool: Thread pool for conversions
        result_future: Future to set with the final result
    """
    # Note that this is run from a top level thread pool, so this doesn't actually block.
    #
    # Create downloader
    downloader = YtDlpDownloader(url, outmp3, cookies_txt=cookies, source=source)

    try:
        # Check for keyboard interrupt
        if check_keyboard_interrupt():
            result_future.set_result(
                (
                    url,
                    outmp3,
                    KeyboardInterruptException(
                        "Download aborted due to previous keyboard interrupt"
                    ),
                )
            )
            return

        # Submit download task and wait for it to complete
        download_future = download_pool.submit(downloader.download)
        download_result = download_future.result()

        # If download failed, set the result and return
        if isinstance(download_result, Exception):
            result_future.set_result((url, outmp3, download_result))
            return

        # Check for keyboard interrupt again before conversion
        if check_keyboard_interrupt():
            result_future.set_result(
                (
                    url,
                    outmp3,
                    KeyboardInterruptException(
                        "Conversion aborted due to previous keyboard interrupt"
                    ),
                )
            )
            return

        # Submit conversion task and wait for it to complete
        convert_future = FFMPEG_EXECUTORS.submit(_process_conversion, downloader)
        conversion_result = convert_future.result()

        # Set the final result
        result_future.set_result(conversion_result)

    except KeyboardInterrupt as e:
        # Handle keyboard interrupt
        set_keyboard_interrupt()
        result_future.set_result((url, outmp3, KeyboardInterruptException(str(e))))
        _thread.interrupt_main()
    except Exception as e:
        # Handle any other exceptions
        result_future.set_result((url, outmp3, e))
    finally:
        # Clean up resources
        downloader.dispose()
