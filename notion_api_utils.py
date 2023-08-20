import os
import requests
import json
import collections
from settings import DEBUG
from typing import NewType
from typing import Dict, List, Any
import inspect


# Define the base Notion_api type
_NotionID = NewType("_NotionID", str)
_NotionObject = NewType("_NotionObjects", Dict[str, Any])
_NotionResponse = NewType("_NotionResponse", Dict[str, Any])


class NotionAPIError(Exception):
    """Base exception class for NotionAPI."""

    pass


class NotionAPI:
    BASE_URL: str = "https://api.notion.com/v1"
    HEADERS: Dict[str, str] = {
        "Authorization": "",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    debug_mode: bool = DEBUG

    def __init__(self, api_key: str):
        if api_key is None:
            raise NotionAPIError("No API key provided.")
        self.HEADERS["Authorization"] = f"Bearer {api_key}"

    # helper methods
    def _handle_response(self, response) -> _NotionResponse:
        """Centralized method to handle API response for debug and error code."""
        status_code = response.status_code
        if self.debug_mode:
            # add the calling function name to the file name as context information
            calling_function_name = inspect.stack()[1].function
            try:
                with open(f".notion_response_from_{calling_function_name}.json", "w") as f:
                    json.dump(response.json(), f, indent=4)
            except:
                # account for the case when response.json() is not json serializable
                print("Failed to write response.json() to file; most likely response is not json serializable.")
        match status_code:
            case 200:
                return response.json()
            case 400:
                error_message = "Bad Request: The request was malformed."
            case 401:
                error_message = "Unauthorized: API token is invalid."
            case 403:
                error_message = "Forbidden: The token does not have access to the requested scope."
            case 404:
                error_message = "Not Found: The resource does not exist."
            case 429:
                error_message = "Too Many Requests: Rate limit exceeded."
            case _:
                error_message = "Unknown error."
        raise NotionAPIError(f"{status_code}: {error_message}")

    def _clean_id(self, id_str: str) -> _NotionID:
        """Remove '-' characters from the given string; consistent id_str format leads to more predictable behavior."""
        return _NotionID(id_str.replace("-", ""))

    # basic endpoints wrappers
    def get_page(self, page_id: _NotionID) -> _NotionObject:
        url = f"{self.BASE_URL}/pages/{self._clean_id(page_id)}"
        response = requests.get(url, headers=self.HEADERS)
        return self._handle_response(response)

    def get_block(self, block_id: _NotionID) -> _NotionObject:
        url = f"{self.BASE_URL}/blocks/{self._clean_id(block_id)}"
        response = requests.get(url, headers=self.HEADERS)
        return self._handle_response(response)

    def create_page(self, database_id: _NotionID, properties: Dict[str, Any]) -> _NotionObject:
        url = f"{self.BASE_URL}/pages"
        data = {"parent": {"database_id": self._clean_id(database_id)}, "properties": properties}
        response = requests.post(url, headers=self.HEADERS, json=data)
        return self._handle_response(response)

    def update_page(self, page_id: _NotionID, properties: Dict[str, Any]) -> _NotionObject:
        url = f"{self.BASE_URL}/pages/{self._clean_id(page_id)}"
        data = {"properties": properties}
        response = requests.patch(url, headers=self.HEADERS, json=data)
        return self._handle_response(response)

    def get_database(self, database_id: _NotionID) -> _NotionObject:
        """units database_id  =  79abdc9bdbc14a1488ae0297bc756145"""
        url = f"{self.BASE_URL}/databases/{self._clean_id(database_id)}"
        response = requests.get(url, headers=self.HEADERS)
        return self._handle_response(response)

    def get_block_children(self, block_id: _NotionID) -> List[_NotionObject]:
        """
        Return a list of response.json() from each API call from the paginated API endpoint
        note the debug mode only writes the response.json() from the last API call to file.
        """
        block_children = []
        url = f"{self.BASE_URL}/blocks/{self._clean_id(block_id)}/children"
        while True:
            response = requests.get(url, headers=self.HEADERS)
            response_json = self._handle_response(response)
            block_children.extend(response_json["results"])
            # If there's more data to fetch
            if response_json["has_more"]:
                url = (
                    f"https://api.notion.com/v1/blocks/{block_id}/children?start_cursor={response_json['next_cursor']}"
                )
            else:
                break
        return block_children

    def append_block_children(self, block_id: _NotionID, children: List[_NotionObject]) -> _NotionObject:
        url = f"{self.BASE_URL}/blocks/{self._clean_id(block_id)}/children"
        data = {"children": children}
        response = requests.patch(url, headers=self.HEADERS, json=data)
        return self._handle_response(response)

    # advanced methods: methods that involves more than one API call
    def unfold_block(self, block_id: _NotionID) -> List[_NotionObject]:
        """
        unfold a block and return a list of all the children blocks recursively,
        with the parent page id attached to each block.
        parent_page_id is the page id of the page that contains the block, which is used in the url construct to refer
        to a block for better visual focus in the Notion UI.
        """
        flat_block_children = []
        block_type = self.get_block(block_id)["type"]
        if block_type != "child_page":
            raise NotionAPIError("currently, method unfold_block() only accepts page_id as input.")
        parent_page_id = block_id  # initialize parent_page_id

        def recursive_unfold_block(block_id: _NotionID):
            nonlocal parent_page_id
            block_type = self.get_block(block_id)["type"]
            parent_page_id = block_id if block_type == "child_page" else parent_page_id
            block_children = self.get_block_children(block_id)
            for block_child in block_children:
                flat_block_children.append(block_child)
                if block_child["has_children"]:
                    recursive_unfold_block(block_child["id"])

        return flat_block_children


class CEPagesManager:
    pass


if __name__ == "__main__":
    api_call = NotionAPI(os.environ.get("NOTION_KEY"))
    api_call.get_block("6bd32fec4c8e4148978e7671d6558a35")
    api_call.get_block_children("6bd32fec4c8e4148978e7671d6558a35")
