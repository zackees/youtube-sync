# pylint: disable=too-many-arguments

"""Library json module."""

import re


def clean_filename(filename: str) -> str:
    """
    Cleans a string to make it a valid directory name by removing emojis,
    special characters, and other non-ASCII characters, in addition to the
    previously specified invalid filename characters, while preserving the file extension.

    Args:
    - filename (str): The filename to be cleaned.

    Returns:
    - str: A cleaned-up string suitable for use as a filename.
    """
    # strip out any leading or trailing whitespace
    filename = filename.strip()
    # strip out leading and trailing periods
    filename = filename.strip(".")
    # strip out multiple periods
    filename = re.sub(r"\.{2,}", ".", filename)
    # Split the filename into name and extension
    name_part, _, extension = filename.rpartition(".")

    # Remove emojis and special characters by allowing only a specific set of characters
    # This regex keeps letters, numbers, spaces, underscores, and hyphens.
    # You can adjust the regex as needed to include any additional characters.
    cleaned_name = re.sub(r"[^\w\s\-_]", "", name_part)

    # Replace spaces or consecutive dashes with a single underscore
    cleaned_name = re.sub(r"\s+|-+", "_", cleaned_name)

    # Replace multiple underscores with a single underscore
    cleaned_name = re.sub(r"_+", "_", cleaned_name)

    # replace commas with underscores
    cleaned_name = cleaned_name.replace(",", "_")

    # remove single quotes
    cleaned_name = cleaned_name.replace("'", "")

    cleaned_name = cleaned_name.replace(":", "_")

    # final problematic characters

    # Replace leading or trailing underscores with an empty string
    cleaned_name = cleaned_name.strip("_")

    # Remove leading or trailing whitespace (after replacing spaces with underscores, this might be redundant)
    cleaned_name = cleaned_name.strip()

    # Optional: Convert to lowercase to avoid issues with case-sensitive file systems
    # cleaned_name = cleaned_name.lower()

    # Optional: Trim the title to a maximum length (e.g., 255 characters)
    max_length = 255
    if len(cleaned_name) > max_length:
        cleaned_name = cleaned_name[:max_length]

    # Reattach the extension only if it was present
    if extension:
        return f"{cleaned_name}.{extension}"
    return cleaned_name
