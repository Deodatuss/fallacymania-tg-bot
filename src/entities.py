import json

from telegram import Update

import constants

_USERS_FILE = constants.JSON_USERS_PATH
_PLAYERS_FILE = constants.JSON_PLAYERS_PATH


def entity_data(update: Update) -> dict:
    user = update.effective_user

    return {
        user.id: {
            "chat_id": update.effective_chat.id,
            "full_name": user.full_name,
            "username": user.username,
            "language_code": user.language_code,
        }
    }


def add_general_user(update: Update) -> None:
    """
    Stores all users that interacted with bot in users.json
    """
    with open(_USERS_FILE, "r") as file:
        data = json.load(file)

    data["users"].append(entity_data(update))

    with open(_USERS_FILE, "w") as file:
        json.dump(data, file)


# not used: data stored as dict inside context.bot_data for I/O economy
def _add_debater(update: Update) -> None:
    """
    Stores active session debaters in players.json
    """
    with open(_PLAYERS_FILE, "r") as file:
        data = json.load(file)

    new_data = entity_data(update)

    data["debaters"].append(new_data)

    with open(_PLAYERS_FILE, "w") as file:
        json.dump(data, file)


# not used: data stored as dict inside context.bot_data for I/O economy
def _add_guesser(update: Update) -> None:
    """
    Stores active session guessers in players.json
    """
    with open(_PLAYERS_FILE, "r") as file:
        data = json.load(file)

    data["guessers"].append(entity_data(update))

    with open(_PLAYERS_FILE, "w") as file:
        json.dump(data, file)
