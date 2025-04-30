from . import utils
from loguru import logger

def get_bookmarks(
    tag: list[str]|None = None,
    date: str|None = None,
    url: str|None = None,
    count: int|None = None,
) -> tuple[dict[str, str], int]:
    """
    Get bookmarks from LinkHut. Supports filtering or fetching recent bookmarks.

    - If 'count' is provided, fetches the most recent 'count' bookmarks, 
      optionally filtered by the first tag in the 'tag' list. Uses /v1/posts/recent.
    - If 'date', 'url', or 'tag' (without 'count') are provided, fetches bookmarks 
      matching the criteria. Uses /v1/posts/get.
    - If no arguments are provided, fetches the 15 most recent bookmarks.

    Args:
        tag (Optional[list[str]]): Filter by tags (for /get) or a single tag (first element used for /recent).
        date (Optional[str]): Filter by date (CCYY-MM-DDThh:mm:ssZ format expected by /get).
        url (Optional[str]): Filter by exact URL (for /get).
        count (Optional[int]): Number of recent bookmarks to fetch (for /recent).

    Returns:
        dict[str, list]: Response dictionary containing bookmarks.
    """
    fields = {}
    api_endpoint = ""

    if count is not None:
        api_endpoint = "/v1/posts/recent"
        fields["count"] = count
        if tag:
            # /v1/posts/recent accept only one tag
            fields["tag"] = tag[0] 
            logger.debug(f"Using first tag for /recent endpoint: {tag[0]}")
    elif tag or date or url:
        api_endpoint = "/v1/posts/get"
        if tag:
            # /v1/posts/get expects tags=tag1+tag2...
            fields["tags"] = ','.join(tag)
        if date:
            # /v1/posts/get takes dt=CCYY-MM-DDThh:mm:ssZ
            fields["dt"] = date # TODO: Add validation/formatting for CCYY-MM-DDThh:mm:ssZ
        if url:
            # utils.verify_url(url)
            fields["url"] = url # TODO: Add URL encoding if necessary utils.encode_url(url)
    else:
        # Default behavior: get recent 15 posts
        api_endpoint = "/v1/posts/recent"
        fields["count"] = 15

    response_obj, response_code = utils.linkhut_api_call(api_endpoint=api_endpoint, fields=fields if fields else None)


    return response_obj, response_code

def create_bookmark(
    url: str,
    title: str|None = None, 
    note: str|None = None, 
    tags: list[str]|None = None,
    fetch_tags: bool = True,
    private: bool = False,
    to_read: bool = False,
    replace: bool = False,
) -> int:
    """
    Create a new bookmark in LinkHut.
    
    Args:
        url (str): The URL to bookmark
        title (Optional[str]): Title for the bookmark. If None, fetches automatically.
        description (Optional[str]): Description for the bookmark
        tags (Optional[List[str]]): List of tags to apply to the bookmark
        private (bool): Whether the bookmark should be private
        
    Returns:
        Dict[str, Any]: The created bookmark data
    """
    utils.verify_url(url)
    
    # If title not provided, try to fetch it
    if title is None:
        try:
            title = utils.get_link_title(url)
            logger.debug(f"Auto-fetched title: {title}")
        except Exception as e:
            logger.warning(f"Failed to auto-fetch title: {e}")
            title = url
    
    # If tags not provided, try to fetch suggestions
    if tags is None and fetch_tags:
        try:
            suggested_tags: list[str] = utils.get_tags_suggestion(url)
            tags = suggested_tags
        except Exception as e:
            logger.warning(f"Failed to auto-suggest tags: {e}")
            tags = []
    
    # Prepare API payload
    fields = {
        "url": url,
        "description": title
    }
    
    if note:
        fields["extended"] = note
    
    if private:
        fields["shared"] = "no"
    
    if tags:
        fields["tags"] = ','.join(tags)
    
    if to_read:
        fields["toread"] = "yes"
    if replace:
        fields["replace"] = "yes"
    
    # Make API call
    api_endpoint = "/v1/posts/add"
    _, status_code = utils.linkhut_api_call(api_endpoint=api_endpoint, fields=fields)

    if status_code == 200:
        logger.debug(f"Bookmark created successfully: {fields}")
    
    return status_code

def reading_list_toggle(url: str, to_read: bool, note: str|None=None, tags:list[str]|None=None) -> bool:

    bookmark_create_status_code: None|int = None

    #check if bookmark with url already exists,
    bookmark_dict, bookmark_exist_status_code = get_bookmarks(url=url)

    # if no, then create a new bookmark with toread=yes'
    if bookmark_exist_status_code == 404:
        logger.debug(f"Bookmark with URL {url} not found. Creating a new one.")
        bookmark_create_status_code = create_bookmark(url=url, to_read=to_read, note=note, tags=tags)

    # if yes
    elif bookmark_exist_status_code == 200:

        # get existing bookmark meta
        logger.debug(f"Bookmark with URL {url} already exists.")
        to_read_current = bookmark_dict.get('posts')[0].get('toread') == 'yes'
        embed_note = bookmark_dict.get('posts')[0].get('extended') #append new note to existing note
        title = bookmark_dict.get('posts')[0].get('description')
        tags = bookmark_dict.get('posts')[0].get('tags').split(',')
        private = bookmark_dict.get('posts')[0].get('shared') == 'no'
        logger.debug(f"Bookmark with URL {url} current status to_read = {to_read_current}, changing to {to_read}")

        # check if toread is already set to the desired value and no new note to append
        if to_read_current == to_read and note is None:
            logger.debug(f"Bookmark with URL {url} already has the desired to_read status. Nothing to do.")
            return False

        # if not, update the bookmark with the new toread status and note
        bookmark_create_status_code = create_bookmark(url=url, title=title, replace=True, to_read=to_read, note=embed_note + note if note else embed_note + '', fetch_tags=False, tags=tags, private=private)

    if bookmark_create_status_code == 200:
        logger.debug(f"Bookmark with URL {url} successfully created or updated to read.")
        return True
    else:
        logger.error(f"Failed to create or update bookmark with URL {url}. Status code: {bookmark_create_status_code}")
        return False

def update_bookmark(url: str, new_tag: list[str]|None = None, new_note: str|None = None, private: bool|None = None) -> bool:
    # todo: add append to tags

    # check if there is nothing to update, if so return false
    if new_tag is not None and new_note is not None and private is not None:
        logger.debug("No updates provided. Nothing to do.")
        return False
    else:
        # check if bookmark with url already exists,
        bookmark_dict, bookmark_exist_status_code = get_bookmarks(url=url)
        # if no, then create a new bookmark with given values
        if bookmark_exist_status_code == 404:
            logger.debug(f"Bookmark with URL {url} not found. Creating a new one.")
            _ = create_bookmark(url=url, tags=new_tag, note=new_note, private=True)
        # if yes
        elif bookmark_exist_status_code == 200:

            # get existing bookmark meta
            bm_data = bookmark_dict.get('posts')[0]
            title = bm_data.get('description')
            tags = new_tag if new_tag else bm_data.get('tags').split(',') #convert str to list
            note = bm_data.get('extended') + new_note if new_note else bm_data.get('extended')
            private = private if private is not None else bm_data.get('shared') == 'no'
            toread = bm_data.get('toread') == 'yes'

            logger.debug(f"Bookmark with URL {url} already exists. Updating it.")
            _ = create_bookmark(url=url, title=title, tags=tags, note=note, private=private, replace=True, fetch_tags=False, to_read=toread)

        logger.debug(f"Bookmark with URL {url} successfully updated.")
        return True
    

def get_reading_list(count:int = 5):
    reading_list, status_code = get_bookmarks(tag=['unread'], count=count)
    if status_code == 200:
        logger.debug(f"Reading list fetched successfully: {reading_list}")
        for i, bookmark in enumerate(reading_list.get('posts')):
            print(f"{i}: Title: {bookmark.get('description')}, URL: {bookmark.get('href')}")

def delete_bookmark(url: str) -> bool:
    """
    Delete a bookmark.
    
    Args:
        bookmark_id (str): ID of the bookmark to delete
        
    Returns:
        Dict[str, Any]: Response from the API
    """
    api_endpoint = "/v1/posts/delete"
    fields = {"url": url}
    
    _, status_code = utils.linkhut_api_call(api_endpoint=api_endpoint, fields=fields)
    
    if status_code == 200:
        logger.debug(f"Bookmark with URL {url} successfully deleted.")
        return True
    else:
        logger.error(f"No bookmark with URL {url} exists. Status code: {status_code}")
        return False

def rename_tag(old_tag: str, new_tag: str) -> bool:
    """
    Rename a tag across all bookmarks.
    
    Args:
        old_tag (str): Current tag name
        new_tag (str): New tag name
        
    Returns:
        Dict[str, Any]: Response from the API
    """
    api_endpoint = "/v1/tags/rename"
    fields = {
        "old": old_tag,
        "new": new_tag
    }
    
    _, status_code = utils.linkhut_api_call(api_endpoint=api_endpoint, fields=fields)
    
    if status_code == 200:
        logger.debug(f"Tag '{old_tag}' successfully renamed to '{new_tag}'.")
        return True
    else:
        logger.error(f"Failed to rename tag '{old_tag}' to '{new_tag}'. Status code: {status_code}")
        return False

def delete_tag(tag: str) -> bool:
    """
    Delete a tag from all bookmarks.
    
    Args:
        tag (str): Tag to delete
        
    Returns:
        Dict[str, Any]: Response from the API
    """
    api_endpoint = "/v1/tags/delete"
    fields = {"tag": tag}
    
    _, status_code = utils.linkhut_api_call(api_endpoint=api_endpoint, fields=fields)
    
    if status_code == 200:
        logger.debug(f"Tag '{tag}' successfully deleted.")
        return True
    else:
        logger.error(f"Failed to delete tag '{tag}'. Tag doesn't exist. Status code: {status_code}")
        return False

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
    url = "https://huggingface.co/blog/gradio-mcp"
    # title = "Example Title"
    # note = "This is a note."
    # tags = ["tag1", "tag2"]
    
    # create_bookmark(url=url)
    # reading_list_toggle(url, to_read=True, tags=['MCP'])
    # update_bookmark(url=url,private=False)
    # delete_bookmark(url)
    # print(get_bookmarks(tag=["repo", "python"]))
    # print(bookmarks)
    get_reading_list(count=5)