import os
import re
import sys
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from loguru import logger

from .config import (
    LINKHUT_API_ENDPOINTS,
    LINKHUT_BASEURL,
    LINKHUT_HEADER,
    LINKPREVIEW_BASEURL,
    LINKPREVIEW_HEADER,
)

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)


def get_request_headers(site: Literal["LinkHut", "LinkPreview"]) -> dict[str, str]:
    """
    Load the PAT from environment variables and return the request headers.
    """
    load_dotenv()  # Load environment variables from .env file

    if site == "LinkHut":
        pat: str | None = os.getenv("LH_PAT")
        if not pat:
            raise ValueError("Error: LH_PAT environment variable not set.")
        header: dict[str, str] = LINKHUT_HEADER
        # Create a copy of the header and format the PAT into it
        request_headers: dict[str, str] = header.copy()
        request_headers["Authorization"] = request_headers["Authorization"].format(PAT=pat)

    elif site == "LinkPreview":
        pat: str | None = os.getenv("LINK_PREVIEW_API_KEY")
        if not pat:
            raise ValueError("Error: LP_API_KEY environment variable not set.")
        header: dict[str, str] = LINKPREVIEW_HEADER
        # Create a copy of the header and format the PAT into it
        request_headers: dict[str, str] = header.copy()
        request_headers["X-Linkpreview-Api-Key"] = request_headers["X-Linkpreview-Api-Key"].format(
            API_KEY=pat
        )

    # logger.debug(f"header for {site} is {request_headers}")
    return request_headers


def make_get_request(url: str, header: dict[str, str]) -> httpx.Response:
    """
    Make a GET request to the specified URL with the provided headers.

    Args:
        url (str): The URL to make the request to.
        header (dict[str, str]): The headers to include in the request.

    Returns:
        httpx.Response: The Response from the request.

    Raises:
        RuntimeError: If the request fails or if the response is not JSON.
        httpx.HTTPStatusError: If the response status code indicates an error (4xx or 5xx).
        httpx.RequestError: If there is a network-related error.
    """
    try:
        logger.debug(f"making get request to following url: {url}")
        response = httpx.get(url=url, headers=header)
        logger.debug(
            f"response is {response.json()} with status code {response.status_code}"  # todo: prettify json output
        )
        return response  # Ensure a response is always returned

    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(
            f"An error occurred while requesting {exc.request.url!r}: {exc}"
        ) from exc
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred: {e}") from e
    

def linkhut_api_call(action: str, fields: dict[str, str] | None) -> httpx.Response:
    """
    Make an API call to the specified LinkHut endpoint and return the response.

    Args:
        action (str): The API action to perform (e.g., "bookmark_create")
        fields (dict[str, str], optional): Query parameters for the request

    Returns:
        Response: The response object from the API
    """
    # Note: Different API endpoints return different data, let the calling function handle the extraction and exception handling.
    # calling functions will define how to handle the exception and the replacement values to use if http request fails.
    url: str = LINKHUT_BASEURL + LINKHUT_API_ENDPOINTS[action]

    # Add query parameters if provided
    if fields:
        url += "?"
        params = []
        for key, value in fields.items():
            params.append(f"{key}={value}")
        url += "&".join(params)

    header = get_request_headers(site="LinkHut")
    logger.debug(f"making request to {url} with header {header}")
    response: httpx.Response = make_get_request(url=url, header=header)
    return response


def get_link_title(dest_url: str) -> str:
    """
    Fetch the title of a link using the LinkPreview API.
    Args:
        dest_url (str): The URL of the link to fetch the title for.

    Returns:
        str: The title of the link.
    """
    # verify_url(url)
    dest_url_str: str = f"q={dest_url}"
    fields_str = "fields=title,description,url"
    api_endpoint: str = f"/?{fields_str}&{dest_url_str}"
    api_url: str = LINKPREVIEW_BASEURL + api_endpoint

    logger.debug(f"fetching title for : {api_url}")

    request_headers: dict[str, str] = get_request_headers("LinkPreview")

def get_tags_suggestion(dest_url: str) -> str:
    """
    Fetch tags suggestion for a link using the LinkHut API.
    Args:
        dest_url (str): The URL of the link to fetch tags for.

    Returns:
        str: A str of suggested tags seperated by comma.

    Note: returns "AutoTagFetchFailed" if the request fails or no suggested tags found.
    """
    action: str = "tag_suggest"
    fields: dict[str, str] = {
        "url": dest_url,
    }

    logger.debug(f"fetching suggested tags for : {dest_url}")

    try:
        response: httpx.Response = linkhut_api_call(action=action, fields=fields)
        # above call will always return a response (200)

        status_code: int = response.status_code
        response_dict: list[dict[str, list[str]]] = response.json()

        if status_code == 200:
            tag_list: list[str] = response_dict[0]["popular"] + response_dict[1]["recommended"]
            if len(tag_list) > 0:
                return ",".join(tag_list)
            else:
                logger.warning(f"No auto tag suggestions found for: {dest_url}")
                return "AutoTagFetchFailed"
        else:
            logger.warning("Issue with the API. Auto Tag Fetch Failed.")
            return "AutoTagFetchFailed"
        
    except Exception as e:
        # if there is a network error or the API is down, we handle that in the following exception.
        logger.error(f"Error fetching tags for {dest_url}: {e}")
        return "AutoTagFetchFailed"


def encode_url(url: str) -> str:
    """
    Encode the URL for use in API calls.
    Args:
        url (str): The URL to encode.

    Returns:
        str: The encoded URL.
    """
    return (
        url.replace(":", "%3A")
        .replace("/", "%2F")
        .replace("?", "%3F")
        .replace("&", "%26")
        .replace("=", "%3D")
        .replace("\\", "%5C")
    )


def verify_url(url: str) -> bool:
    """
    Verify if the URL is valid.
    Args:
        url (str): The URL to verify.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    # Check if the URL starts with a valid scheme
    if not re.match(r"^(http|https)://", url):
        raise ValueError("Invalid URL: must start with http:// or https://")

    if len(url) > 2048:
        raise ValueError("Invalid URL: length exceeds 2048 characters")

    return True


if __name__ == "__main__":
    # Example usage
    dest_url = "http://news.ycombinator.com"
    dest_url_base = dest_url.split("?")[0]

    # print(f"Title info: {get_link_title(dest_url)}")
    # print(f"Tags suggestion: {get_tags_suggestion(dest_url_base)}")
    # print(f"verify url: {verify_url(dest_url)}")
    print(encode_url("\n Now I've read this"))
