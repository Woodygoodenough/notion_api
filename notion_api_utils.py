import os
import requests
import json
import collections
from settings import DEBUG
from typing import NewType, Union, Dict, List, Any
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
                error_message = "Bad Request: The request was malformed"
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

    def create_page(
        self, database_id: _NotionID, properties: Dict[str, Any], children: List[_NotionObject]
    ) -> _NotionObject:
        url = f"{self.BASE_URL}/pages"
        data = {"parent": {"database_id": self._clean_id(database_id)}, "properties": properties, "children": children}
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

    def query_database(self, database_id: _NotionID, filter: Dict[str, Any]) -> List[_NotionObject]:
        children = []
        url = f"{self.BASE_URL}/databases/{self._clean_id(database_id)}/query"
        while True:
            data = {"filter": filter}
            response = requests.post(url, headers=self.HEADERS, json=data)
            response_json = self._handle_response(response)
            children.extend(response_json["results"])
            if response_json["has_more"]:
                url = f"https://api.notion.com/v1/databases/{database_id}/query?start_cursor={response_json['next_cursor']}"
            else:
                break
        return children

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
        if block_type not in ("child_page", "child_database"):
            raise NotionAPIError("currently, method unfold_block() only accepts page_id or database_id as input.")
            print(block_type)
        parent_page_id = block_id

        def recursive_unfold_block(block_id: _NotionID, parent_page_id: _NotionID):
            block_children = self.get_block_children(block_id)
            for block_child in block_children:
                block_child["parent_page_id"] = parent_page_id
                flat_block_children.append(block_child)
                if block_child["has_children"]:
                    parent_page_id = block_child["id"] if block_child["type"] == "child_page" else parent_page_id
                    recursive_unfold_block(block_child["id"], parent_page_id)

        recursive_unfold_block(block_id, parent_page_id)  # start of the recursion

        return flat_block_children

    def extract_units(self, block_id: _NotionID) -> List[_NotionObject]:
        """Return a list of unit blocks."""
        units_blocks = []
        block_children = self.unfold_block(block_id)
        for block in block_children:
            unit_block = self._markdown_criteria_for_units(block)
            if unit_block:
                units_blocks.append(unit_block)
        if self.debug_mode:
            print(f"Found {len(units_blocks)} units.")
        return units_blocks

    def _markdown_criteria_for_units(self, block: _NotionObject) -> Union[int, str]:
        """
        this helper method returns either a valid "unit" string or False, serving as a
        filter for the extract_units()
        """
        if block["type"] == "bulleted_list_item":
            for rich_text in block["bulleted_list_item"]["rich_text"]:
                # Check for bold and italic annotations
                if rich_text["annotations"]["bold"] and rich_text["annotations"]["italic"]:
                    block["unit"] = rich_text["plain_text"]
                    return block
        return False

    def url_for_extracted_unit(self, unit_block: _NotionObject) -> str:
        """Return a list of reference urls for each unit."""
        if "unit" not in unit_block:
            raise KeyError("unit_block does not have a 'unit' key.")

        parent_page_id = self._clean_id(unit_block["parent_page_id"])
        block_id = self._clean_id(unit_block["id"])
        url = f"https://www.notion.so/{parent_page_id}?pvs=4#{block_id}"
        return url


class CEPagesManager:
    WORDDATABASE_ID = "a9d64a44ea8844088612055786f85954"
    MAINDATABASE_ID = "aaa18f4dfc56495e835e0289cbe25f3b"
    debug_mode: bool = DEBUG

    def __init__(self, api_key: str):
        self.notion_api_call = NotionAPI(api_key)

    def refresh_word_database_with_contexts(
        self, word_database_id: _NotionID = WORDDATABASE_ID, main_data_base_id: _NotionID = MAINDATABASE_ID
    ):
        """
        main entry point for now, refresh the designated database with the units extracted from the designated contexts
        """
        contexts = self.get_contexts_from_database(main_data_base_id)
        units_blocks = []
        for context in contexts:
            units_blocks.extend(self.notion_api_call.extract_units(context["id"]))
        for unit_block in units_blocks:
            self.append_unit_to_database(word_database_id, unit_block)

    def append_unit_to_database(self, database_id: _NotionID, unit_block: _NotionObject) -> _NotionObject:
        """
        append units to the database with the given database_id
        """
        unit_name = unit_block["unit"]
        unit_url = self.notion_api_call.url_for_extracted_unit(unit_block)
        properties = {
            "title": {"title": [{"text": {"content": unit_name}}]}
        }  # Assuming all homographs have the same spelling
        children = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": unit_name,
                                "link": {"url": unit_url},
                            },
                        },
                    ]
                },
            }
        ]
        return self.notion_api_call.create_page(database_id, properties, children)

    def get_contexts_from_database(self, database_id: _NotionID) -> List[_NotionObject]:
        filter = {"property": "type", "multi_select": {"contains": "Contexts"}}
        contexts = self.notion_api_call.query_database(database_id, filter)
        for context in contexts:
            if context["object"] != "page":
                raise NotionAPIError("'Contexts' type in the database contains non-page items.")
        return contexts


if __name__ == "__main__":
    ce = CEPagesManager(os.environ["NOTION_KEY"])
    ce.refresh_word_database_with_contexts()
