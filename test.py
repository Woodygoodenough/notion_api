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


def get_block_info(block_id):
    api_url = f"https://api.notion.com/v1/blocks/{block_id}"
    response = requests.get(api_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to get block info. Status code: {response.status_code}")
        print(response.json())
        return None
    return response.json()


if __name__ == "__main__":
    block_id = "a4f6c5f7-0f8b-4e2e-9c7d-5e9a9f1f4e1f"
    block_info = get_block_info(block_id)
    print(json.dumps(block_info, indent=4))
