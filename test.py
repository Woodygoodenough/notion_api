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


"""
fetch sub_blocks from page or block, unfold any nested blocks, return a list of all blocks within
note the argument block_id can be either a page_id or a block_id, and the return list will not include the block of
the id
"""
"""

def append_linked_block_to_target_block(target_block_id, unit, source_block_id, source_page_id):
   

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



def extract_units_from_blocks(blocks):
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
"""
from notion_api_utils import *
from wm_api_utils import *


def from_contexts_to_units(unfolding_page_id: str = "6bd32fec4c8e4148978e7671d6558a35"):
    blocks = unfold_block(unfolding_page_id, debug_mode=DEBUG)
    units = extract_units_from_blocks(blocks)
    print(json.dumps(units, indent=4))
    for unit, source_id in units.items():
        page_id = create_entry_for_a_word(unit)
        source_page_id, source_block_id = [clean_id(id) for id in source_id[0]]
        add_contexts_links_to_unit_page_comments(page_id, source_page_id, source_block_id)
        if DEBUG:
            print(f"https://www.notion.so/{source_page_id}#{source_block_id}")


def create_entry_for_a_word(word: str):
    words_database_id = "a9d64a44ea8844088612055786f85954"
    word_response = get_word_mw_response(word)
    if word_response["error"]:
        print(word_response["message"])
        return None
    word_data = word_response["data"]
    page_id = create_notion_page_for_a_word(words_database_id, word, word_data)
    return page_id


if __name__ == "__main__":
    from_contexts_to_units()
