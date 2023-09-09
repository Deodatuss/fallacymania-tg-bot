"""
Helper bot that recieves a sticker, get JSON data on it's stickerset and stores 
some of stickers' info in a data/deck.json file to be fetched during the game.
"""
import asyncio

import json
from time import sleep

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from get_token import get_token
import deck_json_builder
import constants

_RAW_JSON_STICKERSET_PATH = constants.RAW_JSON_STICKERSET_PATH


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "This bot will take any sticker and turn it's set into a deck"
        " for the FallacyMania bot game. Send a sticker to begin."
    )


async def get_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Save the sticker set associated with this sticker as a deck?"
        "\n If yes, send /save command and it will become a new deck."
    )
    context.user_data["last_sticker_set"] = update.message.sticker.set_name


async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sticker_set_name = context.user_data.get("last_sticker_set")

    if sticker_set_name:
        sticker_set = await context.bot.get_sticker_set(sticker_set_name)

        with open(_RAW_JSON_STICKERSET_PATH, "w") as json_file:
            json_file.write(sticker_set.to_json())

        await update.message.reply_text(
            "Deck " + str(sticker_set_name) + " saved successfully."
        )
    else:
        await update.message.reply_text("You haven't send any sticker yet.")


async def get_deck(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    with open(deck_json_builder._JSON_DECK_PATH, "r") as json_file:
        data = json.load(json_file)

    for i in range(1):
        file_id = data["stickers"][i]["file_id"]
        await update.message.reply_sticker(file_id)

        # is needed if want to output whole range of cards one by one
        sleep(1)


def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder().token(get_token()).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("save", save))
    application.add_handler(CommandHandler("get_deck", get_deck))
    application.add_handler(MessageHandler(filters.Sticker.ALL, get_sticker))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())
