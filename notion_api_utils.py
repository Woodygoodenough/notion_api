import os
import requests
import json
import collections
from settings import DEBUG

NOTION_TOKEN = os.environ.get("NOTION_KEY")
DATA_BASE_ID = "79abdc9bdbc14a1488ae0297bc756145"
NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def get_block_info(block_id: str, debug_mode=False):
    api_url = f"https://api.notion.com/v1/blocks/{block_id}"
    response = requests.get(api_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to get block info. Status code: {response.status_code}")
        print(response.json())
        return None
    if debug_mode:
        with open(".test_block_info.json", "w") as f:
            json.dump(response.json(), f, indent=4)
    return response.json()


def detect_block_type(block_id: str):
    block_info = get_block_info(block_id)
    return block_info["type"]


def get_block_children(block_id):
    api_url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    response = requests.get(api_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to get block children. Status code: {response.status_code}")
        print(response.json())
        return None
    return response.json()


def append_linked_block_to_target_block(target_block_id, unit, source_block_id, source_page_id):
    """
    Create a block, which contains a link to a source block, and append it to the target block.
    the url is essential for notion to direct any link to the original block
    here's an enducated guess for its structure:

    https://www.notion.so/{OptionalDescriptiveText}{PageID}{OptionalParameters}#{BlockID}
    1. "www.": required for the link to work, if omitted, notion client will not try to open the link in itself, but to delegate it to the browser
    1. {BlockID}: if contained, loaded with this block focused.
    2. {PageID}: the Notion page to be loaded. Found right before the '#' or optional parameters.
    3. {OptionalDescriptiveText}: Looks like Notion's parser just ignores it. But once a link is created,
    it is automatically filled with the title of the page followed by "-".
    4. {OptionalParameters}: No idea what they are for, they are always automatically added as "?psv=4" once a link is created.
    5. Parsing Direction: Notion appears to process the URL from right to left, prioritizing BlockID, followed by PageID.

    In summary, for the good of this project, I only use PageID and BlockID for simplicity, and I don't see obvious issues.
    """

    api_url = f"https://api.notion.com/v1/blocks/{target_block_id}/children"
    # Creating a text block with the extracted unit and a link to the original block
    data = {
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": unit,
                                "link": {
                                    "type": "url",
                                    "url": f"https://www.notion.so/{source_page_id}?pvs=4#{source_block_id}",
                                },
                            },
                        }
                    ],
                },
            }
        ]
    }

    response = requests.patch(api_url, headers=HEADERS, json=data)
    if response.status_code != 200:
        print(f"Failed to create block in Notion. Status code: {response.status_code}")
        print(response.json())


def unfold_block(page_id, debug_mode=False):
    """
    fetch sub_blocks from page or block, unfold any nested blocks, return a list of all blocks within
    note the argument block_id can be either a page_id or a block_id, and the return list will not include the block of
    the id
    """
    block_children = []
    if detect_block_type(page_id) != "child_page":
        print("Not a page id")
        return None
    parent_page_id = page_id

    def fetch_notion_block_children_recursive(block_id):
        nonlocal parent_page_id
        print("start fetching blocks", block_id)
        block_type = detect_block_type(block_id)
        if block_type == "child_page":
            parent_page_id = block_id

        url = f"https://api.notion.com/v1/blocks/{block_id}/children"

        while True:
            response = requests.get(url, headers=HEADERS)
            if response.status_code != 200:
                print(f"Failed to fetch Notion block children. Status code: {response.status_code}")
                break

            data = response.json()
            # add each result
            for result in data["results"]:
                result["parent_page_id"] = parent_page_id
                block_children.append(result)
                if result["has_children"]:
                    fetch_notion_block_children_recursive(result["id"])

            # If there's more data to fetch
            if data["has_more"]:
                url = f"https://api.notion.com/v1/blocks/{block_id}/children?start_cursor={data['next_cursor']}"
            else:
                # If no more data to fetch from the current block, break the loop and finish fetching, code returns to
                # the higher level of recursion
                break

    fetch_notion_block_children_recursive(page_id)

    if debug_mode:
        with open(".flat_blokcs.json", "w") as f:
            json.dump(block_children, f, indent=4)

    return block_children


def extract_units_from_blocks(blocks, debug_mode=False):
    units = collections.defaultdict(list)

    for block in blocks:
        # Check if block type is 'bulleted_list_item'
        if block["type"] == "bulleted_list_item":
            for rich_text in block["bulleted_list_item"]["rich_text"]:
                # Check for bold and italic annotations
                if rich_text["annotations"]["bold"] and rich_text["annotations"]["italic"]:
                    units[rich_text["plain_text"]].append((block["parent_page_id"], block["id"]))
    return units


def get_database_info(database_id, debug_mode=False):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"

    # Filter by the 'tags' property of the "select" type, which has the value "Contexts"
    data = {"filter": {"property": "Tags", "select": {"equals": "Contexts"}}}

    response = requests.post(url, headers=HEADERS, json=data)
    pages = response.json()["results"]

    if response.status_code != 200:
        print(f"Failed to query database. Status code: {response.status_code}")
        return None
    return pages


def clean_id(id_str):
    """Remove '-' characters from the given string."""
    return id_str.replace("-", "")


def create_notion_page_for_a_word(database_id: str, word: str, word_data: list):
    # Base structure for the Notion page
    url = f"https://api.notion.com/v1/pages"
    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "title": {"title": [{"text": {"content": word}}]}
        },  # Assuming all homographs have the same spelling
        "children": [],
    }

    for entry in word_data:
        # Extracting data from the Merriam-Webster response for each homograph
        phonetic_spelling = entry["hwi"]["prs"][0]["mw"] if "prs" in entry["hwi"] else ""
        part_of_speech = entry["fl"]
        definitions = entry["shortdef"]
        # Add phonetic spelling, part of speech, and definitions for each homograph
        data["children"].extend(
            [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": phonetic_spelling}}]},
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": part_of_speech}}]},
                },
            ]
        )

        # Add definitions as bulleted list
        for definition in definitions:
            data["children"].append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"text": {"content": definition}}]},
                }
            )
    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code != 200:
        print(f"Failed to create Notion page. Status code: {response.status_code}")
        print(response.json())
        return None
    # Debug mode
    if DEBUG:
        with open(f".{word}_notion_response.json", "w") as f:
            json.dump(response.json(), f, indent=4)
    page_id = response.json()["id"]
    return page_id


def add_contexts_links_to_unit_page_comments(
    page_id: str, source_page_id: str, source_block_id: str, context_text: str = "test_context"
):
    url = "https://api.notion.com/v1/comments"
    data = {
        "parent": {"page_id": page_id},
        "rich_text": [
            {
                "type": "text",
                "text": {
                    "content": context_text,
                    "link": {
                        "type": "url",
                        "url": f"https://www.notion.so/{source_page_id}?pvs=4#{source_block_id}",
                    },
                },
            }
        ],
    }
    response = requests.post(url, headers=HEADERS, json=data)
    status_code_verification(response)
    return response.json()


def append_block_children(block_id: str):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    data = {
        "children": [
            {
                "object": "block",
                "type": "embed",
                "embed": {
                    "url": "https://media.merriam-webster.com/audio/prons/en/us/mp3/p/pajama02.mp3",
                    "caption": [
                        {"type": "text", "text": {"content": "Pronunciation audio."}},
                    ],
                },
            }
        ]
    }
    response = requests.patch(url, headers=HEADERS, json=data)
    status_code_verification(response)
    return response.json()


def status_code_verification(response):
    if response.status_code != 200:
        print(f"Failed to create block in Notion. Status code: {response.status_code}")
        print(response.json())


class NotionAPI:
    BASE_URL = "https://api.notion.com/v1"
    HEADERS = {
        "Authorization": "Bearer YOUR_NOTION_SECRET_API_TOKEN",
        "Notion-Version": "2021-05-13",  # This might need to be updated based on the API version you're using
        "Content-Type": "application/json",
    }

    def __init__(self, api_token):
        self.HEADERS["Authorization"] = f"Bearer {api_token}"

    def get_page(self, page_id):
        url = f"{self.BASE_URL}/pages/{page_id}"
        response = requests.get(url, headers=self.HEADERS)
        return response.json()

    def create_page(self, database_id, properties):
        url = f"{self.BASE_URL}/pages"
        data = {"parent": {"database_id": database_id}, "properties": properties}
        response = requests.post(url, headers=self.HEADERS, json=data)
        return response.json()

    def update_page(self, page_id, properties):
        url = f"{self.BASE_URL}/pages/{page_id}"
        data = {"properties": properties}
        response = requests.patch(url, headers=self.HEADERS, json=data)
        return response.json()

    def get_database(self, database_id):
        url = f"{self.BASE_URL}/databases/{database_id}"
        response = requests.get(url, headers=self.HEADERS)
        return response.json()

    # Add more methods as needed for other endpoints


if __name__ == "__main__":
    append_block_children("48a683e7af77428b8586c2868e0988e4")
