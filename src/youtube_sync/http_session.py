# pylint: disable=line-too-long,missing-class-docstring,missing-function-docstring,consider-using-f-string,too-many-locals,invalid-name
# mypy: ignore-errors

"""
Test script for opening a youtube channel and getting the latest videos.
"""

from threading import Lock

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_SESSION = None
_SESSION_LOCK = Lock()

_MAX_POOL_CONNECTIONS = 10
_MAX_POOL_SIZE = 30


def http_session() -> requests.Session:
    """Get or create a requests session with proper connection pooling."""
    global _SESSION
    with _SESSION_LOCK:
        if _SESSION is None:
            _SESSION = requests.Session()
            # Configure connection pooling
            adapter = HTTPAdapter(
                pool_connections=_MAX_POOL_CONNECTIONS,  # Number of connection pools
                pool_maxsize=_MAX_POOL_SIZE,  # Connections per pool
                max_retries=Retry(
                    total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
                ),
            )
            _SESSION.mount("http://", adapter)
            _SESSION.mount("https://", adapter)
    return _SESSION
