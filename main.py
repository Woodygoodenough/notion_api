from notion_api_utils import *
from wm_api_utils import *


def from_contexts_to_units():
    debug_mode = True
    unfold_block("7650f74465864a788ed4dc7ba92131c6", debug_mode=debug_mode)
    with open(".results.json", "r") as f:
        blocks = json.load(f)
    units = extract_units_from_blocks(blocks)
    print(json.dumps(units, indent=4))
    target_block_id = "0ec528b8540a44e9b01d4e596000fc84"
    for unit, source_id in units.items():
        source_page_id, source_block_id = [clean_id(id) for id in source_id[0]]
        append_linked_block_to_target_block(target_block_id, unit, source_block_id, source_page_id)
        print(f"https://www.notion.so/{source_page_id}#{source_block_id}")


def create_pages_for_units(word):
    words_database_id = "a9d64a44ea8844088612055786f85954"
    word_response = get_word_mw_response(word)
    if word_response["error"]:
        print(word_response["message"])
        return None
    word_data = word_response["data"]
    create_notion_page_for_a_word(words_database_id, word_data)


if __name__ == "__main__":
    create_pages_for_units("idiosyncratic")
