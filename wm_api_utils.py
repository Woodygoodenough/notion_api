import os
import requests
import json
import re
from settings import DEBUG


class MWAPIError(Exception):
    """Base class for exceptions in this module."""

    pass


class MerriamWebsterAPI:
    BASE_URL = "https://www.dictionaryapi.com/api/v3/references/collegiate/json/"

    def __init__(self, api_key: str):
        if not api_key:
            raise MWAPIError("No API key provided")
        self.api_key = api_key

    def get_word_mw_response(self, word):
        # Construct the URL
        url = f"{self.BASE_URL}{word}?key={self.api_key}"

        # Make the request
        response = requests.get(url)
        if DEBUG:
            print(json.dumps(response.json(), indent=4))
        return self._handling_response(response)

    def _handling_response(self, response):
        # Extract data from the response
        response_json = response.json() if response.status_code == 200 else None
        # DEBUG mode
        if DEBUG:
            with open(f".mw_response.json", "w") as f:
                json.dump(response_json, f, indent=4)

        # Check if the request was successful and the data is a list
        if not response_json or not isinstance(response_json, list):
            raise MWAPIError(
                f"Error fetching data or unexpected data format: status_code = {response.status_code}; data = {response_json}"
            )
        if "shortdef" not in response_json[0]:
            raise MWAPIError(
                f"Error, most likely word not found and list of suggestions returned: data = {response_json}"
            )

        return response_json

    def response_to_CE(self, response_json: dict):
        """method to convert the response to a simple version to be used for now"""
        word_simple_dicts_list = []
        for entry in response_json:
            word_entry = {}
            word_entry["show_word"]: str = entry["meta"]["id"].split(":")[0]
            word_entry["hw"]: str = entry["hwi"]["hw"].replace("*", "·​")
            word_entry["fl"]: str = entry["fl"] if "fl" in entry else ""
            word_entry["defs"]: list[str] = entry["shortdef"]
            word_entry["prs"]: list[dict[str, str]] = []
            if "prs" in entry["hwi"]:
                for pr in entry["hwi"]["prs"]:
                    pr_dict = {}
                    pr_dict["mw"] = pr["mw"] if "mw" in pr else ""
                    pr_dict["sound"] = self.mw_audio_url_construct(pr["sound"]) if "sound" in pr else ""
                    word_entry["prs"].append(pr_dict)
            word_simple_dicts_list.append(word_entry)
        return word_simple_dicts_list

    def mw_audio_url_construct(self, sound: dict, format: str = "mp3"):
        """
        return an audio url given a sound object in mw_response
        """
        audio = sound["audio"]
        if audio.startswith("bix"):
            sub_dir = "bix"
        elif audio.startswith("gg"):
            sub_dir = "gg"
        # if audio begins with a number or punctuation (eg, "_"), the subdirectory should be "number"
        elif re.match(r"^[0-9_]", audio):
            sub_dir = "number"
        else:
            sub_dir = audio[0]
        url = f"https://media.merriam-webster.com/audio/prons/en/us/mp3/{sub_dir}/{audio}.{format}"
        return url


if __name__ == "__main__":
    mw = MerriamWebsterAPI(api_key=os.environ.get("MERRIAM_WEBSTER_KEY"))
    response_json = mw.get_word_mw_response("contingency")

    print(json.dumps(mw.response_to_CE(response_json), indent=4))
