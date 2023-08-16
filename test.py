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


def create_unit_block_in_notion(target_page_id, unit, source_block_id):
    """
    Create a block in Notion page with the extracted unit.
    """
    url = f"https://api.notion.com/v1/blocks/{target_page_id}/children"

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
                                "link": {"type": "url", "url": f"https://www.notion.so/{source_block_id}"},
                                # www is required for the link to work, if omitted, notion client will not try to
                                # open the link in itself, but to delegate it to the browser
                            },
                        }
                    ],
                },
            }
        ]
    }

    response = requests.patch(url, headers=HEADERS, json=data)
    if response.status_code != 200:
        print(f"Failed to create block in Notion. Status code: {response.status_code}")
        print(response.json())


if __name__ == "__main__":
    target_page_id = "0ec528b8540a44e9b01d4e596000fc84"
    # source_block_id = "984597286ac04aeb8198e1602e4ff477"
    # source_block_id = "2f4d86c4512d4cb4b4148c0745591a62"
    source_block_id = "Practice_1-984597286ac04aeb8198e1602e4ff477?pvs=4#2f4d86c4512d4cb4b4148c0745591a62"
    unit = "Penance"
    create_unit_block_in_notion(target_page_id, unit, source_block_id)
