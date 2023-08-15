import os
import requests
import re
import json

NOTION_TOKEN = os.environ.get("NOTION_KEY")
NOTION_PAGE_ID = "aaa18f4dfc56495e835e0289cbe25f3b"
NOTION_VERSION = "2022-06-28"
HEADERS = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": NOTION_VERSION}


# Fetch all children of a Notion block or page
def fetch_all_notion_block_children(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    all_results = []

    i = 0
    while True:
        response = requests.get(url, headers=HEADERS)

        if response.status_code != 200:
            print(f"Failed to fetch Notion block children. Status code: {response.status_code}")
            break

        data = response.json()
        i += 1
        with open(f".response_page_{i}.json", "w") as f:
            json.dump(data, f, indent=4)

        # Add the results from this chunk to the all_results list
        all_results.extend(data["results"])

        # If there's more data to fetch
        if data["has_more"]:
            # Set the URL for the next request
            url = f"https://api.notion.com/v1/blocks/{block_id}/children?start_cursor={data['next_cursor']}"
        else:
            # If there's no more data, break the loop
            break

    return all_results


# Extract units from content
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


if __name__ == "__main__":
    results = fetch_all_notion_block_children(NOTION_PAGE_ID)

    # load content into a json file for test purpose
    with open(".content.json", "w") as f:
        json.dump(results, f, indent=4)

    if results:
        units = extract_units_from_content(results)
        print(units)
