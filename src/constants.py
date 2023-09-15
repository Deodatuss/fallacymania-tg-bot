import os
from typing import TypedDict

RAW_JSON_STICKERSET_PATH = os.path.join(
    os.path.dirname(__file__), "../tmp/raw_sticker_set.json"
)

JSON_DECK_PATH = os.path.join(os.path.dirname(__file__), "../data/sticker_deck.json")

JSON_PLAYERS_PATH = os.path.join(os.path.dirname(__file__), "../config/players.json")

JSON_USERS_PATH = os.path.join(os.path.dirname(__file__), "../config/players.json")

PDF_CARDS_FILE_NAME = "Fallacymania-fallacies-rus.pdf"
PDF_CARDS_PATH = os.path.join(
    os.path.dirname(__file__), f"../data/{PDF_CARDS_FILE_NAME}"
)

DEBATERS_DICT_KEY = "debater"
GUESSERS_DICT_KEY = "guesser"


class Debater(TypedDict):
    chat_id: int
    full_name: str
    username: str
    language_code: str
    hand: dict[str, int]  # file_unique_id: message_id


class Points(TypedDict):
    score: int
    attempts: int


class Guesser(TypedDict):
    chat_id: int
    full_name: str
    username: str
    language_code: str
    points: Points


class BotData(TypedDict):
    debater: dict[int, Debater]
    guesser: dict[int, Guesser]
    free_deck: list
    is_game_started: bool
    deck_data: dict
    active_cards: dict[str]
