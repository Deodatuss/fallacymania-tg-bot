"""
Bot that recieves a sticker, get JSON data on it's stickerset and stores 
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


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start() -> None:
    pass


async def get_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        """
        Save the sticker set associated with this sticker as a deck?
        \n If yes, send /save command and it will become a new deck. 
        """
    )
    sticker: Sticker = update.message.sticker
    # my_set: StickerSet = await context.bot.get_sticker_set(my_sticker.set_name)
    # print(my_set.to_json)
    context.user_data["last_sticker_id"] = sticker.file_id
    context.user_data["last_sticker_set"] = sticker.set_name


async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # update.message.reply_sticker(
    #     update.effective_chat.id,
    # )
    if context.user_data.get("last_sticker_id"):
        await update.message.reply_sticker(context.user_data.get("last_sticker_id"))
    else:
        await update.message.reply_text("You haven't sent any sticker yet.")


def main() -> None:
    """Run the bot."""
    application = ApplicationBuilder.token(get_token()).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("save", save))
    application.add_handler(MessageHandler(filters.Sticker.ALL, get_sticker))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    asyncio.run(main())
