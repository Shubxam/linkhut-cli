"""LinkHut Library - Core functions for interacting with LinkHut API.

This module provides functions for managing bookmarks and tags through the LinkHut API,
including creating, updating, listing and deleting bookmarks, as well as managing tags.
"""

import sys

from httpx import Response
from loguru import logger

from . import utils

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)


def get_bookmarks(
    tag: str = "",
    date: str = "",
    url: str = "",
    count: int | None = None,
) -> list[dict[str, str]]:
    """
    Get bookmarks from LinkHut. Supports filtering or fetching by recent count.

    - If 'count' is provided, fetches the most recent 'count' bookmarks,
      optionally filtered by the first tag in the 'tag' list. Uses /v1/posts/recent.
    - If 'date', 'url', or 'tag' (without 'count') are provided, fetches bookmarks
      matching the criteria. Uses /v1/posts/get.
    - If no arguments are provided, fetches the 15 most recent bookmarks.

    Args:
        tag (str): Filter by tags (for /get) or a single tag (first element used for /recent).
        date (str): Filter by date (CCYY-MM-DDThh:mm:ssZ format expected by /get).
        url (str): Filter by exact URL (for /get).
        count (int|None): Number of recent bookmarks to fetch (for /recent).

    Returns:
        list[dict]: list of dictionaries containing bookmark metadata.
    """
    fields: dict[str, str] = {}
    action: str

    if count is not None:
        action = "bookmark_recent"
        fields["count"] = str(count)  # if count is 0, then returns 15
        if tag:
            # bookmark_recent accept only one tag, if multiple tags are provided, then only the first one is used
            # if presented with wrong tag, it returns {"posts": []}
            fields["tag"] = tag.replace(",", " ").split()[0]
            logger.debug(f"Using first tag for /recent endpoint: {fields['tag']}")
    elif tag or date or url:
        action = "bookmark_get"
        if tag:
            # bookmark_get expects tags=tag1+tag2...
            fields["tag"] = tag.replace(" ", "+").replace(",", "+")
        if date:
            try:
                # bookmark_get takes dt=CCYY-MM-DD
                utils.is_valid_date(date)  # validate date format
            except ValueError as e:
                logger.error(f"Invalid date format for {date}: {e}")
                return [{"error": "invalid_date_format"}]
            fields["dt"] = date
        if url:
            try:
                # TODO: Add URL encoding if necessary utils.encode_url(url)
                utils.verify_url(url)
            except ValueError as e:
                logger.error(f"Invalid URL format for {url}: {e}")
                return [{"error": "invalid_url_format"}]
            fields["url"] = url
    else:
        # Default behavior: get recent 15 posts
        action = "bookmark_recent"
        fields["count"] = "15"

    try:
        response: Response = utils.linkhut_api_call(
            action=action, payload=fields
        )
        fetched_bookmarks: list[dict[str, str]] = response.json().get("posts", [])

        # if bookmarks are found, posts list will not be empty
        if fetched_bookmarks:
            logger.debug("Bookmarks fetched successfully")
            return fetched_bookmarks
        elif response.json().get("result_code") == "something went wrong" or not fetched_bookmarks:
            # result code "something went wrong" indicates posts/get endpoint was called with wrong url
            logger.error("No Bookmarks Found")
            return [{"error": "no_bookmarks_found"}]
        else:
            logger.warning("No bookmarks found for the given criteria")
            return [{"error": "unknown_error"}]
    except Exception as e:
        logger.error(f"Error fetching bookmarks: {e}")
        return [{"error": "error_fetching_bookmarks"}]


def create_bookmark(
    url: str,
    title: str = "",
    note: str = "",
    tags: str = "",  # could be of form: "tag1,tag2" or "tag1 tag2" or "tag1 tag2,tag3" 
    fetch_tags: bool = True,
    private: bool = False,
    to_read: bool = False,
    replace: bool = False,
) -> dict[str, str]:
    """
    Create a new bookmark in LinkHut.

    This function creates a new bookmark with the specified URL and optional metadata.
    If title is not provided, it will attempt to fetch the title automatically from the URL.
    If tags are not provided and fetch_tags is True, it will attempt to suggest tags based on the URL content.

    Args:
        url (str): The URL to bookmark
        title (str): Title for the bookmark. If None, fetches automatically.
        note (str): Extended notes or description for the bookmark
        tags (str): Comma-separated list of tags to apply to the bookmark
        fetch_tags (bool): Whether to auto-suggest tags if none provided (default: True)
        private (bool): Whether the bookmark should be private (default: False)
        to_read (bool): Whether to mark the bookmark as "to read" (default: False)
        replace (bool): Whether to replace an existing bookmark with the same URL (default: False)

    Returns:
        dict[str, str]: The created bookmark's metadata
    """
    try:
        # must start with http:// or https://
        utils.verify_url(url)
    except Exception as e:
        logger.error(f"Invalid URL: {url}. Error: {e}")
        return {"status": "invalid_url"}
    
    action = "bookmark_create"

    # If title not provided, try to fetch it
    if not title:        
        title = utils.get_link_title(url)

    # If valid tags not provided, try to fetch suggestions
    if not tags.isalnum() and fetch_tags:
        tags_str: str = utils.get_tags_suggestion(url)  # comma separated tags
        tags = tags_str.replace(",", " ").replace(" ", "+")  # convert to + separated tags

    # checks if tag string in argument is not just a whitespace or empty string
    elif tags.isalnum():  
        _tag_list: list[str] = tags.replace(",", " ").split()
        tags = "+".join(_tag_list)

    # Prepare API payload
    fields: dict[str, str] = {}
    fields['url'] = url
    fields["description"] = title
    fields["tags"] = tags
    fields["replace"] = "yes" if replace else "no"
    fields["toread"] = "yes" if to_read else "no"
    fields["shared"] = "no" if private else "yes"

    if note:
        fields["extended"] = note

    try:
        response: Response = utils.linkhut_api_call(action=action, payload=fields)
        response_dict: dict[str, str] = response.json()
        status_code: int = response.status_code
        if status_code == 200 and response_dict.get("result_code") == "done":
            logger.debug(f"Bookmark created successfully: {response_dict}")
            return fields
        else:
            logger.error(f"Failed to create bookmark: {response_dict}")
            return {"status": "bookmark already exists"}
    except Exception as e:
        logger.error(f"Error creating bookmark: {e}")
        return {"status": "API error"}


def reading_list_toggle(
    url: str, 
    to_read: bool, 
    note: str = "",
    tags: str = ""
) -> dict[str, str]:
    """
    Toggle the to-read status of a bookmark.

    This function either updates an existing bookmark's to-read status or creates a new
    bookmark with the specified to-read status if it doesn't exist.

    Args:
        url (str): The URL of the bookmark to toggle
        to_read (bool): Whether to mark as to-read (True) or read (False)
        note (Optional[str]): Note to append to the bookmark if provided
        tags (Optional[list[str]]): Tags to add if creating a new bookmark, append to existing tags if updating

    Returns:
        bool: True if the operation was successful, False otherwise
    """

    # check for existing bookmark with the given URL
    fetched_bookmark: dict[str, str] = get_bookmarks(url=url)[0]
    fields_to_inherit: set[str] = {"toread", "extended", "description", "tags", "shared"}

    # if bookmark not found, then create a new bookmark
    if fetched_bookmark.get("error") == "no_bookmarks_found":
        logger.debug(f"Bookmark with URL {url} not found. Creating a new one.")
        bookmark_meta: dict[str, str] = create_bookmark(
            url=url, to_read=to_read, note=note, tags=tags
        )
        return bookmark_meta

    elif fetched_bookmark.get("error") == "invalid_url_format":
        logger.debug(f"Invalid URL format: {url}. Please provide a valid URL.")
        # propagate the error to the calling function
        return {"error": "invalid_url_format"}

    # if bookmark exists, then update the bookmark
    # proper api result should contain all fields_to_inherit
    elif fields_to_inherit.issubset(fetched_bookmark.keys()):
        # get existing bookmark meta
        logger.debug(f"Bookmark with URL {url} already exists.")
        to_read_current: bool = fetched_bookmark.get("toread", "yes") == "yes"
        embed_note: str = fetched_bookmark.get("extended", "")
        title: str = fetched_bookmark.get("description", url)
        current_tags: str = fetched_bookmark.get("tags", "")
        private: bool = fetched_bookmark.get("shared", "yes") == "no"
        logger.debug(
            f"Bookmark with URL {url} current status to_read = {to_read_current}, changing to {to_read}"
        )

        # check if toread is already set to the desired value and no new note to append
        if to_read_current == to_read and note is None:
            logger.info(
                f"Bookmark with URL {url} already has the desired to_read status. Nothing to do."
            )
            return {"status": "no_update_needed"}

        # if not, update the bookmark with the new toread status and note
        bookmark_meta: dict[str, str] = create_bookmark(
            url=url,
            title=title,
            replace=True,
            to_read=to_read,
            note=embed_note + note if note else embed_note,
            fetch_tags=False,
            tags=current_tags if not tags else current_tags + " " + tags,
            private=private,
        )
        return bookmark_meta
    else:
        logger.debug("Unexpected bookmark format received. Missing required fields.")
        return {"error": "unknown_error"}


# todo: #19 update_bookmark and reading_list_toggle functions can be merged into one function
def update_bookmark(
    url: str,
    new_tag: str = "",
    new_note: str = "",
    new_private: str = "",
    replace: bool = False,  # whether to replace data or append to existing data
) -> dict[str, str]:
    """
    Update an existing bookmark or create a new one if it doesn't exist.

    This function allows updating the tags, notes, and privacy settings of a bookmark.
    If the bookmark doesn't exist, it will create a new one with the provided parameters.

    Args:
        url (str): The URL of the bookmark to update
        new_tag (Optional[list[str]]): New tags to set for the bookmark (replaces existing tags)
        new_note (Optional[str]): Note to append to the existing note
        private (Optional[bool]): Whether to set the bookmark as private (True) or public (False)

    Returns:
        bool: True if the update was successful, False otherwise
    """

    # check if there is nothing to update, if so return false
    if not new_tag and not new_note and not new_private:
        logger.debug("No updates provided. Nothing to do.")
        return {"status": "missing_update_parameters"}
    else:
        fields_to_inherit: set[str] = {"description", "tags", "extended", "shared", "toread"}

        # check for existing bookmark with the given URL
        fetched_bookmark: dict[str, str] = get_bookmarks(url=url)[0]

        # if no, then create a new bookmark with given values
        if fetched_bookmark.get("error") == "no_bookmarks_found":
            logger.debug(f"Bookmark with URL {url} not found. Creating a new one.")
            bookmark_meta: dict[str, str] = create_bookmark(url=url, tags=new_tag, note=new_note, private=False)
            return bookmark_meta
        
        elif fetched_bookmark.get("error") == "invalid_url_format":
            logger.debug(f"Invalid URL format: {url}. Please provide a valid URL.")
            # propagate the error to the calling function
            return {"error": "invalid_url_format"}
        
        elif fetched_bookmark.get("error"):
            logger.debug("Unexpected error occurred while fetching bookmark data.")
            return {"error": "unknown_error"}
        
        # if yes
        elif fields_to_inherit.issubset(fetched_bookmark.keys()):
            # get existing bookmark meta
            title: str = fetched_bookmark.get("description", url)
            tags: str = fetched_bookmark.get("tags", "")
            note: str = fetched_bookmark.get("extended", "")
            toread: bool = fetched_bookmark.get("toread", "yes") == "yes"
            if new_private is not None:
                # if new_private is provided, use it, otherwise use existing value
                private: bool = True if new_private == "yes" else False
            else:
                # if new_private is not provided, use existing value
                private: bool = fetched_bookmark.get("shared", "yes") == "no"

            logger.info(f"Bookmark with URL {url} already exists. Updating it.")
            bookmark_meta = create_bookmark(
                url=url,
                title=title,
                tags=new_tag if replace else tags + " " + new_tag if new_tag else tags,
                note=new_note if replace else note + " " + new_note if new_note else note,
                private=private,
                replace=True,
                fetch_tags=False,
                to_read=toread,
            )
            return bookmark_meta
        else:
            logger.debug("Unexpected bookmark format received. Missing required fields.")
            return {"error": "unknown_error"}


def get_reading_list(count: int = 5) -> list[dict[str, str]]:
    """
    Fetch and display the user's reading list (bookmarks marked as to-read).

    Args:
        count (int): Number of bookmarks to fetch (default: 5)

    Returns:
        None: Results are printed directly to stdout
    """
    reading_list: list[dict[str, str]] = get_bookmarks(tag="unread", count=count)
    if reading_list[0].get("error"):
        logger.error("No bookmarks found in the reading list.")
        return [{"error": "no_bookmarks_found"}]
    elif reading_list:
        logger.debug(f"Reading list fetched successfully: {reading_list}")
        return reading_list
    else:
        logger.error("No bookmarks found in the reading list.")
        return [{"error": "no_bookmarks_found"}]


def delete_bookmark(url: str) -> dict[str, str]:
    """
    Delete a bookmark.

    Args:
        bookmark_id (str): ID of the bookmark to delete

    Returns:
        Dict[str, Any]: Response from the API
    """
    action: str = "bookmark_delete"
    fields: dict[str, str] = {"url": url}

    try:
        # verify the URL format before making the API call
        utils.verify_url(url)
        response: Response = utils.linkhut_api_call(action=action, payload=fields)
    except ValueError as e:
        logger.error(f"Invalid URL format: {url}. Error: {e}")
        return {"error": "invalid_url_format"}
    except Exception as e:
        logger.error(f"Error deleting bookmark: {e}")
        return {"error": "api_error"}
    
    result_code: str = response.json().get("result_code", "")

    if result_code == "done":
        logger.debug(f"Bookmark with URL {url} successfully deleted.")
        return {"bookmark_deletion": "success"}
    else:
        logger.error(f"Unable to delete bookmark with URL {url}. Result code: {result_code}")
        return {"bookmark_deletion": "unsuccessful"}


def rename_tag(old_tag: str, new_tag: str) -> dict[str, str]:
    """
    Rename a tag across all bookmarks.

    Args:
        old_tag (str): Current tag name
        new_tag (str): New tag name

    Returns:
        Dict[str, Any]: Response from the API
    """
    action = "tag_rename"
    fields = {"old": old_tag, "new": new_tag}

    try:
        # verify the tag format before making the API call
        if not old_tag.isalnum() or not new_tag.isalnum():
            raise ValueError(f"Invalid tag format: {old_tag} or {new_tag}")
        response: Response = utils.linkhut_api_call(action=action, payload=fields)
    except ValueError as e:
        logger.error(f"Invalid tag format: {old_tag} or {new_tag}. Error: {e}")
        return {"error": "invalid_tag_format"}
    except Exception as e:
        logger.error(f"Error renaming tag: {e}")
        return {"error": "api_error"}
    
    result_code: str = response.json().get("result_code", "")

    if result_code == "done":
        logger.info(f"Tag '{old_tag}' successfully renamed to '{new_tag}'.")
        return {"tag_renaming": "success"}
    else:
        logger.error(f"Failed to rename tag '{old_tag}' to '{new_tag}'. Result code: {result_code}")
        return {"tag_renaming": "unsuccessful"}


# todo: #20 update error handling for delete_tag, rename_tag
def delete_tag(tag: str) -> dict[str, str]:
    """
    Delete a tag from all bookmarks.

    Args:
        tag (str): Tag to delete

    Returns:
        Dict[str, Any]: Response from the API
    """
    action: str = "tag_delete"
    fields: dict[str, str] = {"tag": tag}

    try:
        # verify the tag format before making the API call
        if not tag.isalnum():
            raise ValueError(f"Invalid tag format: {tag}")
        response: Response = utils.linkhut_api_call(action=action, payload=fields)
    except ValueError as e:
        logger.error(f"Invalid tag format: {tag}. Error: {e}")
        return {"error": "invalid_tag_format"}
    except Exception as e:
        logger.error(f"Error deleting tag: {e}")
        return {"error": "api_error"}
    
    result_code: str = response.json().get("result_code", "")

    if result_code == "done":
        logger.debug(f"Tag '{tag}' successfully deleted.")
        return {"tag_deletion": "success"}
    else:
        logger.error(f"Failed to delete tag '{tag}'. Tag doesn't exist. Result code: {result_code}")
        return {"tag_deletion": "unsuccessful"}


# def get_tags() -> List[Dict[str, Any]]:
#     """
#     Get all tags and their counts.

#     Returns:
#         List[Dict[str, Any]]: List of tags with counts
#     """
#     api_endpoint = "/v1/tags"
#     fields = {}

#     response = utils.linkhut_api_call(api_endpoint=api_endpoint, fields=fields)

#     return response


if __name__ == "__main__":
    # Example usage
    # These examples show how to use the library functions directly
    # Uncomment any of these lines to test the functionality

    # url = "https://huggingface.co/blog/gradio-mcp"
    # title = "Example Title"
    # note = "This is a note."
    # tags = ["tag1", "tag2"]

    # 1. Create a new bookmark
    # create_bookmark(url=url)

    # 2. Mark a bookmark as to-read
    # reading_list_toggle(url, to_read=True, tags=['MCP'])

    # 3. Update a bookmark's privacy setting
    # update_bookmark(url=url, private=False)

    # 4. Delete a bookmark
    # delete_bookmark(url)

    # 5. List bookmarks with a specific tag
    print(get_bookmarks(tag=["blog"]))

    # 6. Show reading list
    # get_reading_list(count=5)
