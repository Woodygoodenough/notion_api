import os
import requests

NOTION_KEY = os.environ.get("NOTION_KEY")
headers = {
    "Authorization": "Bearer " + NOTION_KEY,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}
search_params = {"filter": {"value": "page", "property": "object"}}
search_response = requests.post(f"https://api.notion.com/v1/search", json=search_params, headers=headers)

print(search_response.json())
