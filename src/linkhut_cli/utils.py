import re


def parse_bulk_items(content: str) -> list[str]:
    """
    Parse a string of items(URLs, tags) separated by newlines, commas, whitespace into a list of items.
    Args:
        content (str): A string containing items separated by newlines, commas, whitespace.
    Returns:
        list[str]: A list of items.
    """
    return [item.strip() for item in re.split(r"[,\n]+", content) if item.strip()]


# TODO: Implement the function to parse linkhut get response to display the bookmark entries


def sanitize_tags(tag_string: str) -> str:
    tag_string = tag_string.strip().replace(",", " ")
    return tag_string
