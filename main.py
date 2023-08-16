import os
import requests
import json

NOTION_TOKEN = os.environ.get("NOTION_KEY")
DATA_BASE_ID = "79abdc9bdbc14a1488ae0297bc756145"
NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def unfold_block(block_id, debug_mode=False):
    """
    fetch sub_blocks from page or block, unfold any nested blocks, return a list of all blocks within
    note the argument block_id can be either a page_id or a block_id, and the return list will not include the block of
    the id
    """
    all_results = []

    def fetch_notion_block_children_recursive(block_id):
        print("start fetching blocks", block_id)
        url = f"https://api.notion.com/v1/blocks/{block_id}/children"

        while True:
            response = requests.get(url, headers=HEADERS)
            if debug_mode:
                print("get the response", block_id)
            if response.status_code != 200:
                print(f"Failed to fetch Notion block children. Status code: {response.status_code}")
                break

            data = response.json()

            # Add the results from this chunk to the all_results list
            all_results.extend(data["results"])

            # If there's more data to fetch
            if data["has_more"]:
                url = f"https://api.notion.com/v1/blocks/{block_id}/children?start_cursor={data['next_cursor']}"
            else:
                # If no more data to fetch from the current block, check its children for nested blocks.
                # Recursively fetch data from these nested blocks and add to the all_results list.
                for result in data["results"]:
                    if result["has_children"]:
                        fetch_notion_block_children_recursive(result["id"])
                break

    fetch_notion_block_children_recursive(block_id)

    if debug_mode:
        with open(".results.json", "w") as f:
            json.dump(all_results, f, indent=4)

    return all_results


def extract_units_from_blocks(blocks, debug_mode=False):
    units = []

    for block in blocks:
        # Check if block type is 'bulleted_list_item'
        if block["type"] == "bulleted_list_item":
            for rich_text in block["bulleted_list_item"]["rich_text"]:
                # Check for bold and italic annotations
                if rich_text["annotations"]["bold"] and rich_text["annotations"]["italic"]:
                    units.append(rich_text["plain_text"])
    return units


def get_data_base_info(database_id, debug_mode=False):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"

    # Filter by the 'tags' property of the "select" type, which has the value "Contexts"
    data = {"filter": {"property": "Tags", "select": {"equals": "Contexts"}}}

    response = requests.post(url, headers=HEADERS, json=data)
    pages = response.json()["results"]

    if response.status_code != 200:
        print(f"Failed to query database. Status code: {response.status_code}")
        return None
    return pages


if __name__ == "__main__":
    debug_mode = True  # Set this to False if you don't want to save to a JSON file
    """
    all_results = fetch_data_from_notion(NOTION_PAGE_ID, debug_mode)

    if all_results:
        units = extract_units_from_content(all_results)
        print(units)
    """
    pages = get_data_base_info(DATA_BASE_ID)

    units = []
    for page in pages:
        notion_id = page["id"]
        blocks = unfold_block(notion_id, debug_mode)
        units.extend(extract_units_from_blocks(blocks))
    print(units)
