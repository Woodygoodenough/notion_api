import os
import json
from notion_api_utils import CEPagesManager
from wm_api_utils import MerriamWebsterAPI, MWAPIError
from settings import DEBUG, _NotionID, _NotionObject, _NotionResponse


class SyntheticOperation:
    MAINDATABASE_ID = "aaa18f4dfc56495e835e0289cbe25f3b"
    WORDDATABASE_ID = "a9d64a44ea8844088612055786f85954"
    EXPRDATABASE_ID = "3670f8bab263462a8e60c6ae8ae88dd8"

    def __init__(self):
        self.CEpages = CEPagesManager(os.environ["NOTION_KEY"])
        self.WMapi = MerriamWebsterAPI(os.environ["MERRIAM_WEBSTER_KEY"])
        self.debug = DEBUG

    def refresh_units_database_with_contexts(
        self,
        word_database_id: _NotionID = WORDDATABASE_ID,
        expression_database_id: _NotionID = EXPRDATABASE_ID,
        main_data_base_id: _NotionID = MAINDATABASE_ID,
    ):
        """
        main entry point for now, refresh the designated database with the units extracted from the designated contexts
        """
        contexts = self.CEpages.get_contexts_from_database(main_data_base_id)
        block_children = []
        units_blocks = []
        child_pages_to_sync = []
        for context in contexts:
            block_children.extend(self.CEpages.unfold_block_and_mark_sync(context["id"])[0])
            child_pages_to_sync.extend(self.CEpages.unfold_block_and_mark_sync(context["id"])[1])
        units_blocks = self.CEpages.extract_units(block_children)
        for unit_block in units_blocks:
            self.append_or_update_unit_in_database(word_database_id, expression_database_id, unit_block)
        # the updation should be the last step to ensure that all in-state sync info are accurate
        # when there is an interruption at this stage, the only consequence is that the already synced pages will be
        # synced again next time
        for child_page in child_pages_to_sync:
            self.CEpages.update_extraction_time(child_page)

    def append_or_update_unit_in_database(
        self, word_database_id: _NotionID, expression_database_id: _NotionID, unit_block: _NotionObject
    ) -> _NotionObject:
        """
        append units to the database with the given database_id
        """
        if_word = True
        database_id = word_database_id
        unit_name = unit_block["unit"]
        # decide if the unit is a word or a phrase
        if " " in unit_name:
            if_word = False
            database_id = expression_database_id
        unit_page_id = self.CEpages.if_unit_in_database(unit_name, database_id)
        unit_url = self.CEpages.url_for_extracted_unit(unit_block)
        # check if the unit is already in the database
        if not unit_page_id:
            simple_dicts = []
            if if_word:
                try:
                    simple_dicts = self.WMapi.response_to_CE(self.WMapi.get_word_mw_response(unit_name))
                    # assuming the first headword is the one we want
                except MWAPIError:
                    print(f"Error fetching data for {unit_name}, skipping...")
                    return None
            unit_page_id = self.page_construct(unit_name, simple_dicts, database_id)["id"]

        self.CEpages.append_new_context_to_unit(unit_name, unit_url, unit_page_id)

    def page_construct(self, unit_name: str, simple_dicts: list[dict], database_id: _NotionID) -> _NotionObject:
        """
        create a new unit page in the given database
        """

        def _properties_construct(title_name: str, pronuciations: list[str] = None):
            properties = {
                "title": {"title": [{"text": {"content": title_name}}]},
            }
            if pronuciations:
                properties["Pronunciation"] = {"rich_text": [{"text": {"content": f"\{pr}\ "}} for pr in pronuciations]}
            return properties

        def _heading_2_obj(text="", link=None, rich_text_runs=None):
            obj = {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": text,
                                "link": link,
                            },
                        }
                    ],
                    "color": "default",
                    "is_toggleable": False,
                },
            }
            if rich_text_runs:
                obj["heading_2"]["rich_text"] = rich_text_runs
            return obj

        def _heading_3_obj(text="", link=None, rich_text_runs=None):
            obj = {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": text,
                                "link": link,
                            },
                        }
                    ],
                    "color": "default",
                    "is_toggleable": False,
                },
            }
            if rich_text_runs:
                obj["heading_3"]["rich_text"] = rich_text_runs
            return obj

        def _bulleted_list_item_obj(text, link=None):
            obj = {
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": text,
                                "link": link,
                            },
                        },
                    ],
                    "color": "default",
                },
            }

            return obj

        def _para_obj(text, link=None, color="default", italic=False):
            obj = {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": text,
                                "link": link,
                            },
                            "annotations": {
                                "italic": italic,
                            },
                        },
                    ],
                    "color": color,
                },
            }
            return obj

        def _embed_obj(url):
            obj = {
                "object": "block",
                "type": "embed",
                "embed": {
                    "url": url,
                },
            }
            return obj

        def _divider_obj():
            obj = {
                "object": "block",
                "type": "divider",
                "divider": {},
            }
            return obj

        def _rich_context_run(**args):
            text = args.get("text", "")
            link = args.get("link", None)
            anno = args.get("anno", {})
            rich_text_obj = {
                "type": "text",
                "text": {
                    "content": text,
                    "link": link,
                },
                "annotations": {
                    "bold": False,
                    "italic": False,
                    "strikethrough": False,
                    "underline": False,
                    "code": False,
                    "color": "default",
                },
            }
            if anno:
                rich_text_obj["annotations"].update(anno)
            return rich_text_obj

        children = []
        if not simple_dicts:
            properties = _properties_construct(unit_name)
            children.append(_heading_2_obj("Contexts"))
            return self.CEpages.notion_api_call.create_page(
                database_id=database_id, properties=properties, children=children
            )
        properties = _properties_construct(
            title_name=simple_dicts[0]["show_word"], pronuciations=[pr["mw"] for pr in simple_dicts[0]["prs"]]
        )
        for idx, entry in enumerate(simple_dicts):
            hw_run = _rich_context_run(text=str(idx + 1) + ". " + entry["hw"])
            fl_run = _rich_context_run(text=" " + entry["fl"], anno={"color": "gray", "italic": True})
            children.append(_heading_3_obj(rich_text_runs=[hw_run, fl_run]))
            for pr in entry["prs"]:
                if pr["mw"]:
                    children.append(_para_obj(pr["mw"]))
                if pr["sound"]:
                    children.append(_embed_obj(pr["sound"]))
            defs_objs_list = [_bulleted_list_item_obj(defi) for defi in entry["defs"]]
            children.extend(defs_objs_list)
            children.append(_divider_obj())
        children.append(_heading_2_obj("Context"))
        with open(".json_view.json", "w") as f:
            json.dump(children, f, indent=4)
        return self.CEpages.notion_api_call.create_page(
            database_id=database_id, properties=properties, children=children
        )


if __name__ == "__main__":
    SO = SyntheticOperation()
    SO.refresh_units_database_with_contexts()
