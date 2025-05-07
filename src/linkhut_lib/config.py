"""
Configuration settings for the LinkHut and LinkPreview APIs.

This module contains the base URLs and header templates for making API requests.
The actual API keys are inserted into these templates at runtime.
"""

# LinkHut API configuration
LINKHUT_HEADER: dict[str, str] = {
    'Accept':'application/json',
    'Authorization':'Bearer {PAT}',  # PAT placeholder replaced at runtime
}
LINKHUT_BASEURL: str = "https://api.ln.ht"

# LinkPreview API configuration
LINKPREVIEW_HEADER: dict[str, str] = {
    "X-Linkpreview-Api-Key": "{API_KEY}"  # API_KEY placeholder replaced at runtime
}
LINKPREVIEW_BASEURL: str = "https://api.linkpreview.net"