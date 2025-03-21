"""
Rumble scrapper.
"""

# pylint: disable=line-too-long,missing-function-docstring,consider-using-f-string,too-many-locals,invalid-name,no-else-return,fixme,too-many-branches,too-many-statements
# mypy: ignore-errors


from youtube_sync.fetch_html import fetch_html_using_curl as fetch_html


def get_channel_url_for_page(channel: str, page_num: int, is_user_channel: bool) -> str:
    # only return a page if the page number is greater than 1
    # if page_num > 1:
    #    if is_user_channel:
    #        return f"https://rumble.com/user/{channel}?page={page_num}"
    #    return f"https://rumble.com/c/{channel}?page={page_num}"
    # if is_user_channel:
    #    return f"https://rumble.com/user/{channel}"
    # return f"https://rumble.com/c/{channel}"
    # let's simplify this
    if is_user_channel:
        base_url = f"https://rumble.com/user/{channel}"
    else:
        base_url = f"https://rumble.com/c/{channel}"
    if page_num > 1:
        return f"{base_url}?page={page_num}"
    return base_url


def to_channel_url(channel: str) -> str:
    test_url = get_channel_url_for_page(
        channel=channel, page_num=1, is_user_channel=False
    )
    fetch_response = fetch_html(test_url)
    if fetch_response.ok:
        return test_url
    test_url = get_channel_url_for_page(
        channel=channel, page_num=1, is_user_channel=True
    )
    fetch_response = fetch_html(test_url)
    if fetch_response.ok:
        return test_url
    raise ValueError(f"Could not find channel or user {channel}")
