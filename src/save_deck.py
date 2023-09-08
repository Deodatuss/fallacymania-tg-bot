"""
Helper bot that recieves a sticker, get JSON data on it's stickerset and stores 
some of stickers' info in a data/deck.json file to be fetched during the game.
"""
import os
import logging
import json
import asyncio

from telegram import Update, StickerSet, Sticker
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters,
)

from get_token import get_token

_SCRIPT_DIR = os.path.dirname(__file__)
_RAW_JSON_STICKER_SET_PATH = "../tmp/raw_sticker_set.json"


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
        json_file_path = os.path.join(_SCRIPT_DIR, _RAW_JSON_STICKER_SET_PATH)

        with open(json_file_path, "w") as json_file:
            json_file.write(sticker_set.to_json())

        await update.message.reply_text("Deck saved successfully.")
    else:
        await update.message.reply_text("You haven't send any sticker yet.")


def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder().token(get_token()).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("save", save))
    application.add_handler(MessageHandler(filters.Sticker.ALL, get_sticker))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())
