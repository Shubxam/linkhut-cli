import re


def parse_bulk_urls(urls: str) -> list[str]:
    """
    Parse a string of URLs separated by newlines or commas into a list of URLs.
    Args:
        urls (str): A string containing URLs separated by newlines or commas.
    Returns:
        list[str]: A list of URLs.
    """
    return [url.strip() for url in re.split(r"[,\n]+", urls) if url.strip()]