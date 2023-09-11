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


async def _read_raw_stickerset_file() -> dict:
    """
    Reads raw JSON file with sticker set info.
    Returns dict with raw data.
    """
    with open(_RAW_JSON_STICKERSET_PATH, "r") as file:
        raw_set_data: dict = json.load(file)
    return raw_set_data


async def _stickerset_to_deck_converter(raw_set_data) -> dict:
    """
    Takes raw_set_data as input, trims most data from
    'stickers' list except emoji, unique_file_id, file_id and file_size.
    Returns dict with a formatted deck.
    """

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

    return deck_data


async def read_deck_file() -> dict:
    """
    Reads sticker deck file directly, without conversion from raw stickerset.
    Returns dict with a deck.
    """
    with open(_JSON_DECK_PATH, "r") as file:
        deck_data: dict = json.load(file)

    return deck_data


async def _save_deck_to_file(deck_data: dict) -> None:
    """
    Saves deck to a dedicated game file.
    """
    with open(_JSON_DECK_PATH, "w") as file:
        json.dump(deck_data, file)


async def main():
    raw_data = await _read_raw_stickerset_file()
    deck_data = await _stickerset_to_deck_converter(raw_data)
    await _save_deck_to_file(deck_data)


if __name__ == "__main__":
    asyncio.run(main())
