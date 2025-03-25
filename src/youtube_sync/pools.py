import os
from concurrent.futures import ThreadPoolExecutor

_MAX_CPU_WORKERS = max(2, os.cpu_count() or 0)

# Thread pool for resolving futures
FUTURE_RESOLVER_POOL = ThreadPoolExecutor(
    max_workers=_MAX_CPU_WORKERS, thread_name_prefix="future_resolver"
)

FFMPEG_EXECUTORS = ThreadPoolExecutor(
    max_workers=_MAX_CPU_WORKERS, thread_name_prefix="ffmpeg_executor"
)
