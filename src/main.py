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
    """
    Generates the game local memory deck, where cards will be pulled from
    as game progresses.
    """
    deck_data = context.bot_data["deck_data"]
    return [i["file_unique_id"] for i in deck_data["stickers"]]


async def generate_hands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends cards to every debater.
    Stores used cards in debater hands, and leaves leftover stickers in a free deck
    """

    free_deck: list = context.bot_data["free_deck"]

    # give N unique stickers to every debater user
    for player in context.bot_data["debater"]:
        context.bot.send_message(
            chat_id=player["chat_id"],
            text=f"Your hand have these {_CARDS_PER_HAND} cards:",
        )
        for i in range(_CARDS_PER_HAND):
            if free_deck.__len__() <= 0:
                update.effective_user.send_message(
                    "free deck was emtied because there are too many debaters or"
                    " some have too many cards. Please re-initialize the game"
                )
                break
            else:
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

        # TODO: initialize score board for guessers and give them attempts to guess
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
    """
    Only works during the game; logic is different based on user role.

    Debater: during start of the game, each debater gets his hand of cards.
    When he wants to use some card, he should either reply with any non-command
    to desired card from a deck, or send the same card from his sticker pack.
    This card will then be set as active. If he wants to use another card,
    he would need to reply to another card or send another sticker.
    Old one will be deleted, to keep things less cluttered.

    Guesser: after sending a sticker user think some debater has used,
    the keyboard is sent to ask, if user really meant to use this sticker.
    After confirmation, the global check is initiated in a function guess_buttons.
    """

    if context.bot_data["is_game_started"]:
        if update.effective_user.id in context.bot_data["debater"]:
            # TODO: write code logic in respect to function comment
            pass
        if update.effective_chat.id in context.bot_data["guesser"]:
            # TODO: write code logic in respect to function comment
            pass
    else:
        update.effective_user.send_message("Sorry, game hasn't started yet.")


async def guess_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Parses the CallbackQuery sent by guesser from 'guess' function.
    Initializes a global check of cards. If card sent by the guesser matches
    any of active card from debaters, guesser gets a point.
    If it doesn't match, guesser loses one 'attempt' (until reaches zero).
    If he has no attempts left, the point is taken from him (can go negative).
    """
    # TODO: implement function by adding another CallbackQuery gandler
    query = update.callback_query
    await query.answer()


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

    # choose a role when entering the room
    application.add_handler(CommandHandler("start", start))
    # TODO: CallbackQueryHandlers should use regex pattern matching of query data
    application.add_handler(CallbackQueryHandler(start_buttons))

    # TODO: add admin function to clear all users roles,
    # e.g. if there is too much debaters

    # basic game start conditions, progress and end conditions
    application.add_handler(CommandHandler("help", help))

    # during game users mostly interact by first sending card to a bot
    application.add_handler(MessageHandler(filters.Sticker.ALL, guess))

    # admin fucntion: start game with all conditions (i.e. score, hands and message)
    application.add_handler(CommandHandler("start_game", start_game))

    # admin function: end game, sending game results to all users
    application.add_handler(CommandHandler("end_game", end_game))

    application.run_polling()


if __name__ == "__main__":
    main()
