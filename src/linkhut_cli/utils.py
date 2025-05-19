import re
from typing import Literal


def parse_bulk_items(content: str, type: Literal["url", "tag"]) -> list[str]:
    """
    Parse a string of items(URLs, tags) separated by newlines, commas, whitespace into a list of items.
    Args:
        content (str): A string containing items separated by newlines, commas, whitespace.
        type (str): The type of items to parse. Can be "url" or "tag".
    Returns:
        list[str]: A list of items.
    """
    if type == "url":
        return [item.strip() for item in re.split(r"[,\n]+", content) if item.strip()]
    elif type == "tag":
        return [item.strip() for item in re.split(r"[,\s]+", content) if item.strip()]