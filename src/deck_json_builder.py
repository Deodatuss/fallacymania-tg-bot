"""
Helper function that takes only relevant data from raw sticker set file
and saves it into data folder to be used as an actual deck.
It keeps the original json data structure, but eliminates useless info.
"""
import json
import asyncio

import constants

_RAW_JSON_STICKERSET_PATH = constants.RAW_JSON_STICKERSET_PATH
_JSON_DECK_PATH = constants.JSON_DECK_PATH


# TODO: split into functions to only convert and only read/write files
async def stickerset_to_deck_converter() -> None:
    """
    Reads raw JSON file with sticker set info, trims most data from
    'stickers' list except emoji, file_id, full file_size.
    Saves trimmed data to another JSON file.
    """

    with open(_RAW_JSON_STICKERSET_PATH, "r") as file:
        raw_set_data: dict = json.load(file)
    deck_data = dict.fromkeys(raw_set_data.keys(), {})

    # copy sticker set meta-info (without stickers)
    for key in deck_data:
        if key != "stickers":
            deck_data[key] = raw_set_data[key]

    # copy only relevant data inside stickers list
    for sticker in raw_set_data["stickers"]:
        deck_data["stickers"][sticker["file_unique_id"]] = {
            "emoji": sticker["emoji"],
            "file_id": sticker["file_id"],
            "file_size": sticker["file_size"],
        }

    with open(_JSON_DECK_PATH, "w") as file:
        json.dump(deck_data, file)


async def main():
    await stickerset_to_deck_converter()


if __name__ == "__main__":
    asyncio.run(main())
