import json

from telegram import Update

import constants

_USERS_FILE = constants.JSON_USERS_PATH
_PLAYERS_FILE = constants.JSON_PLAYERS_PATH


async def entity_data(update: Update) -> dict:
    user = update.effective_user

    return {
        "id": user.id,
        "full_name": user.full_name,
        "username": user.username,
        "language_code": user.language_code,
    }


async def add_general_user(update: Update) -> None:
    """
    Stores all users that interacted with bot in users.json
    """
    with open(_USERS_FILE, "r") as file:
        data = json.load(file)

    data["users"].append(entity_data(update))

    with open(_USERS_FILE, "w") as file:
        json.dump(data, file)


async def add_debater(update: Update) -> None:
    """
    Stores active session debaters in players.json
    """
    with open(_PLAYERS_FILE, "r") as file:
        data = json.load(file)

    data["debaters"].append(entity_data(update))

    with open(_PLAYERS_FILE, "w") as file:
        json.dump(data, file)


async def add_guesser(update: Update) -> None:
    """
    Stores active session guessers in players.json
    """
    with open(_PLAYERS_FILE, "r") as file:
        data = json.load(file)

    data["guessers"].append(entity_data(update))

    with open(_PLAYERS_FILE, "w") as file:
        json.dump(data, file)
