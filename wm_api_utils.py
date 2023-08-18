import os
import requests
import json
from settings import DEBUG

# Your Merriam-Webster API Key
MW_API_KEY = os.environ.get("MERRIAM_WEBSTER_KEY")

# Endpoint for the Merriam-Webster Collegiate Dictionary
MW_BASE_URL = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"


def get_word_mw_response(word):
    # Construct the URL
    url = f"{MW_BASE_URL}{word}?key={MW_API_KEY}"

    # Make the request
    response = requests.get(url)

    # Extract data from the response
    data = response.json() if response.status_code == 200 else None
    # DEBUG mode
    if DEBUG:
        with open(f".{word}_mw_response.json", "w") as f:
            json.dump(data, f, indent=4)

    # Check if the request was successful and the data is a list
    if not data or not isinstance(data, list):
        return {
            "error": True,
            "message": f"Error fetching data or unexpected data format: status_code = {response.status_code}; data = {data}",
        }
    if "shortdef" not in data[0]:
        return {
            "error": True,
            "message": f"Error, most likely word not found and list of suggestions returned: data = {data}",
        }

    return {"error": False, "data": data}
