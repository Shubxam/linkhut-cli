"""
Configuration settings for the LinkHut and LinkPreview APIs.

This module contains the base URLs and header templates for making API requests.
The actual API keys are inserted into these templates at runtime.
"""
# todo: make use of ENUMs and TypeAlias and Dataclasses

# from enum import Enum
# from typing import TypeAlias

# LinkHut API configuration
LINKHUT_HEADER: dict[str, str] = {
    "Accept": "application/json",
    "Authorization": "Bearer {PAT}",  # PAT placeholder replaced at runtime
}
LINKHUT_BASEURL: str = "https://api.ln.ht"

# LinkHut API endpoints
LINKHUT_API_ENDPOINTS: dict[str, str] = {
    "bookmark_get": "/v1/posts/get",
    "bookmark_recent": "/v1/posts/recent",
    "bookmark_create": "/v1/posts/add",
    "bookmark_delete": "/v1/posts/delete",
    "tag_suggest": "/v1/posts/suggest",
    "tag_delete": "/v1/tags/delete",
    "tag_rename": "/v1/tags/rename",
}


# LinkPreview API configuration
LINKPREVIEW_HEADER: dict[str, str] = {
    "X-Linkpreview-Api-Key": "{API_KEY}"  # API_KEY placeholder replaced at runtime
}
LINKPREVIEW_BASEURL: str = "https://api.linkpreview.net"
