import os
import requests
import json

NOTION_TOKEN = os.environ.get("NOTION_KEY")
NOTION_PAGE_ID = "79abdc9bdbc14a1488ae0297bc756145"
NOTION_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def fetch_data_from_notion(page_id, debug_mode=False):
    """
    Fetches data from a Notion page and returns a list of an exhaustive list of all blocks (including nested ones)
    on the page.
    """
    all_results = []

    def fetch_notion_block_children_recursive(block_id):
        url = f"https://api.notion.com/v1/blocks/{block_id}/children"

        while True:
            response = requests.get(url, headers=HEADERS)

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

    fetch_notion_block_children_recursive(page_id)

    if debug_mode:
        with open(".results.json", "w") as f:
            json.dump(all_results, f, indent=4)

    return all_results


def extract_units_from_content(results):
    units = []

    for block in results:
        # Check if block type is 'bulleted_list_item'
        if block["type"] == "bulleted_list_item":
            for rich_text in block["bulleted_list_item"]["rich_text"]:
                # Check for bold and italic annotations
                if rich_text["annotations"]["bold"] and rich_text["annotations"]["italic"]:
                    units.append(rich_text["plain_text"])
    return units


def get_the_data_base_info(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"

    # Filter by the 'contexts' property having a value (is not empty)
    data = {
        "filter": {
            "or": [
                {"property": "Tags", "contains": "contexts"},
            ]
        }
    }

    data_1 = {
        "filter": {
            "or": [
                {"property": "In stock", "checkbox": {"equals": True}},
                {"property": "Cost of next trip", "number": {"greater_than_or_equal_to": 2}},
            ]
        },
        "sorts": [{"property": "Last ordered", "direction": "ascending"}],
    }

    response = requests.post(url, headers=HEADERS, json=data)

    print(json.dumps(response.json(), indent=4))

    if response.status_code != 200:
        print(f"Failed to query database. Status code: {response.status_code}")
        return None


if __name__ == "__main__":
    debug_mode = False  # Set this to False if you don't want to save to a JSON file
    """
    all_results = fetch_data_from_notion(NOTION_PAGE_ID, debug_mode)

    if all_results:
        units = extract_units_from_content(all_results)
        print(units)
    """
    get_the_data_base_info(NOTION_PAGE_ID)
