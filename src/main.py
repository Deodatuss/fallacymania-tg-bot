import random
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from get_token import get_token
import entities

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

_DEBATER_NAME = "Debater"
_GUESSER_NAME = "Guesser"
_HELP_TEXT = (
    "there should be some help, but have these at least:",
    " http://fallacymania.com/game",
)
_CARDS_PER_HAND = 5


async def _move_to_role(
    dict_key: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Helper function. If user is not saved by bot, let him choose a role.
    User can have only one role (except extra admin role), and his data inside
    dict amongst average roles is not duplicated.
    """
    all_keys = list(context.bot_data.keys())

    # admins is unique role, which is not dependent on other roles
    try:
        all_keys.remove("admin")
    except ValueError:
        pass

    for key in all_keys:
        # if user is already in average roles dict
        if update.effective_user.id in context.bot_data[key]:
            context.bot_data[key].pop(update.effective_user.id)

    # add him again with specified role
    context.bot_data[dict_key].update(entities.entity_data(update))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(_DEBATER_NAME, callback_data="debater")],
        [InlineKeyboardButton(_GUESSER_NAME, callback_data="guesser")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Please choose your role:", reply_markup=reply_markup
    )


async def start_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the start message text."""
    query = update.callback_query.from_user
    await query.answer()

    if query.data == "debater":
        await _move_to_role("debater", update, context)
        await query.edit_message_text(text=f"You are now a {_DEBATER_NAME}")
    elif query.data == "guesser":
        await _move_to_role("guesser", update, context)
        await query.edit_message_text(text=f"You are now a {_GUESSER_NAME}")
    else:
        await query.edit_message_text(
            text=f"Something went wrong with choosing a role."
        )


async def generate_free_deck(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> list:
    deck_data = context.bot_data["deck_data"]
    return [i["file_unique_id"] for i in deck_data["stickers"]]


async def generate_hands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """store used cards in debater hands, and leave leftover stickers in a free deck"""

    free_deck: list = context.bot_data["free_deck"]

    # give N unique stickers to every debater user
    for player in context.bot_data["debater"]:
        context.bot.send_message(
            chat_id=player["chat_id"],
            text=f"Your hand have these {_CARDS_PER_HAND} cards:",
        )
        for i in range(_CARDS_PER_HAND):
            if free_deck.__len__() <= 0:
                context.bot_data["free_deck"] = await generate_free_deck()
                update.effective_user.send_message(
                    "free deck was emtied because there are too many debaters or"
                    " some have too many cards; generated new free deck"
                )
            # pop random card's unique_id from a free deck
            given_card = free_deck.pop(random.choice(free_deck))

            # get file_id which is used to send a sticker
            file_id = context.bot_data["deck_data"][given_card]["file_id"]

            message: Message = context.bot.send_sticker(
                chat_id=player["chat_id"], sticker=file_id
            )

            # add this unique_id and it's message_id to user's hand
            context.bot_data["debater_hand"].update({given_card: message.id})


async def guess_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pass


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.bot_data["is_game_started"] is True:
        update.message.reply_text("Game already in progress")
    else:
        deck_data = context.bot_data["deck_data"]

        # generate new free deck that will be shrinked as game progresses
        context.bot_data["free_deck"] = await generate_free_deck(update, context)

        # generate hands and broadcast these hands to debaters
        await generate_hands(update, context)
        # for player in context.bot_data["debater"]:
        #     await context.bot.send_message(
        #         chat_id=context.bot_data["debater"][player]["chat_id"],
        #         text="oh hi, game started",
        #     )

        # broadcast start rules to guessers
        for player in context.bot_data["guesser"]:
            await context.bot.send_message(
                chat_id=context.bot_data["guesser"][player]["chat_id"],
                text=(
                    "Game started. Send cards you want to guess, then you'll"
                    " be able to pick a debater."
                ),
            )
    pass


async def guess(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if (
        update.effective_chat.id in context.bot_data["guesser"]
        and context.bot_data["is_game_started"]
    ):
        keyboard = [
            [
                InlineKeyboardButton(
                    debater["full_name"],
                    callback_data=debater,
                )
            ]
            for debater in context.bot_data["debaters"]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Please choose who you're trying to guess: :", reply_markup=reply_markup
        )
    else:
        update.message.delete()
        message: Message = update.message.reply_text("You can't guess a debater yet.")
        context.bot.delete_message(update.effective_chat.id, message.id)
    pass


async def guess_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery, updates the guess text, and sends request to dabater."""
    query = update.callback_query
    await query.answer()

    # send sticker and keyboard to debater, asking if this is the sticker


async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # broadcast game results to all users

    pass


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "".join(_HELP_TEXT)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)


def main() -> None:
    application = ApplicationBuilder().token(get_token()).build()

    # initialize player storage dicts
    application.bot_data["debater"] = {}
    application.bot_data["debater_hand"] = {}
    application.bot_data["guesser"] = {}
    application.bot_data["admin"] = {}
    application.bot_data["is_game_started"] = False
    application.bot_data["free_deck"] = []

    # load deck so bot could send stickers by their id
    application.bot_data["deck_data"] = entities.get_deck()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("start_game", start_game))
    application.add_handler(CommandHandler("end_game", end_game))
    application.add_handler(CommandHandler("guess", guess))
    application.add_handler(CallbackQueryHandler(start_buttons, pattern))

    application.run_polling()


if __name__ == "__main__":
    main()
