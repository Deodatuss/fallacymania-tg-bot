import json

from telegram import Update

import constants

_USERS_FILE = constants.JSON_USERS_PATH
_PLAYERS_FILE = constants.JSON_PLAYERS_PATH
_JSON_DECK_PATH = constants.JSON_DECK_PATH
_DEBATERS_DICT_KEY = constants.DEBATERS_DICT_KEY
_GUESSERS_DICT_KEY = constants.GUESSERS_DICT_KEY


def get_deck() -> dict:
    """Returns dict of cards, which is used in game"""
    with open(_JSON_DECK_PATH, "r") as file:
        data = json.load(file)

    return data


def get_debater(update: Update) -> dict:
    user = update.effective_user
    hand = {}

    data: constants.Debater = {
        "chat_id": update.effective_chat.id,
        "full_name": user.full_name,
        "username": user.username,
        "language_code": user.language_code,
        "hand": hand,
        "score": 0,
    }

    return {user.id: data}


def get_guesser(update: Update) -> dict:
    user = update.effective_user
    points: constants.Points = {"score": 0, "attempts": 0}

    data: constants.Guesser = {
        "chat_id": update.effective_chat.id,
        "full_name": user.full_name,
        "username": user.username,
        "language_code": user.language_code,
        "points": points,
    }

    return {user.id: data}


def entity_data(bot_data_dict_key: str, update: Update) -> dict:
    if bot_data_dict_key == _DEBATERS_DICT_KEY:
        return get_debater(update)
    elif bot_data_dict_key == _GUESSERS_DICT_KEY:
        return get_guesser(update)
    raise KeyError


# Currently not used; entities are for program runtime only

# def add_general_user(update: Update) -> None:
#     """
#     Stores all users that interacted with bot in users.json
#     """
#     with open(_USERS_FILE, "r") as file:
#         data = json.load(file)

#     data["users"].append(entity_data(update))

#     with open(_USERS_FILE, "w") as file:
#         json.dump(data, file)


# # not used: data stored as dict inside context.bot_data for I/O economy
# def _add_debater(update: Update) -> None:
#     """
#     Stores active session debaters in players.json
#     """
#     with open(_PLAYERS_FILE, "r") as file:
#         data = json.load(file)

#     new_data = entity_data(update)

#     data["debaters"].append(new_data)

#     with open(_PLAYERS_FILE, "w") as file:
#         json.dump(data, file)


# # not used: data stored as dict inside context.bot_data for I/O economy
# def _add_guesser(update: Update) -> None:
#     """
#     Stores active session guessers in players.json
#     """
#     with open(_PLAYERS_FILE, "r") as file:
#         data = json.load(file)

#     data["guessers"].append(entity_data(update))

#     with open(_PLAYERS_FILE, "w") as file:
#         json.dump(data, file)
