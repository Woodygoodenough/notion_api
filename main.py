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
