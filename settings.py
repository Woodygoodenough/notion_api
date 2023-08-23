DEBUG = True
from typing import NewType, Dict, Any

# datatypes
# Define the base Notion_api type
_NotionID = NewType("_NotionID", str)
_NotionObject = NewType("_NotionObjects", Dict[str, Any])
# object type when accessing a page with page or database endpoint
_NotionPage = NewType("_NotionPage", Dict[str, Any])
# object type when accessing a page with block endpoint
_NotionChildPage = NewType("_NotionChildPage", Dict[str, Any])
_NotionResponse = NewType("_NotionResponse", Dict[str, Any])
