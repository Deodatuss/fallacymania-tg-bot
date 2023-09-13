import random
import logging
from time import sleep

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
import constants

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
_DEBATERS_DICT_KEY = constants.DEBATERS_DICT_KEY
_GUESSERS_DICT_KEY = constants.GUESSERS_DICT_KEY


async def _move_to_role(
    bot_data_dict_key: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Helper function. If user is not saved by bot, let him choose a role.
    User can have only one role (except extra admin role), and his data inside
    dict amongst average roles is not duplicated.
    """
    # admin is unique role, which is not dependent on other roles
    role_keys = [_DEBATERS_DICT_KEY, _GUESSERS_DICT_KEY]

    for key in role_keys:
        # if user is already in average roles dict
        if update.effective_user.id in context.bot_data[key]:
            context.bot_data[key].pop(update.effective_user.id)

    # add him again with specified role
    context.bot_data[bot_data_dict_key].update(
        entities.entity_data(bot_data_dict_key, update)
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                _DEBATER_NAME, callback_data=f"start-{_DEBATERS_DICT_KEY}"
            )
        ],
        [
            InlineKeyboardButton(
                _GUESSER_NAME, callback_data=f"start-{_GUESSERS_DICT_KEY}"
            )
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Please choose your role:", reply_markup=reply_markup
    )


async def start_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the start CallbackQuery and updates the start message text."""
    query = update.callback_query
    await query.answer()

    if context.bot_data["is_game_started"]:
        update.effective_user.send_message(
            "Sorry, you can't choose a role while active game is in progress."
        )
    else:
        if query.data == f"start-{_DEBATERS_DICT_KEY}":
            await _move_to_role(_DEBATERS_DICT_KEY, update, context)
            await query.edit_message_text(text=f"You are now a {_DEBATER_NAME}")
        elif query.data == f"start-{_GUESSERS_DICT_KEY}":
            await _move_to_role(_GUESSERS_DICT_KEY, update, context)
            await query.edit_message_text(text=f"You are now a {_GUESSER_NAME}")
        else:
            await query.edit_message_text(
                text="Something went wrong with CallbackQuery."
            )


async def generate_free_deck(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> list:
    """
    Generates the game new local memory deck, where cards will be pulled from
    as game progresses.
    Returns shuffled list of stickers' unique_id.
    """
    deck_stickers = context.bot_data["deck_data"]["stickers"]
    deck = [key for key in deck_stickers]
    random.shuffle(deck)
    return deck


async def generate_hands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends cards to every debater.
    Stores used cards in debater hands, and leaves leftover stickers in a free deck
    """
    # generate new free deck that will be shrinked as game progresses
    context.bot_data["free_deck"] = await generate_free_deck(update, context)
    free_deck: list = context.bot_data["free_deck"]

    # give N unique stickers to every debater user
    for player, values in context.bot_data["debater"].items():
        await context.bot.send_message(
            chat_id=values["chat_id"],
            text=f"Your hand have these {_CARDS_PER_HAND} cards:",
        )
        for i in range(_CARDS_PER_HAND):
            if free_deck.__len__() <= 0:
                await update.effective_user.send_message(
                    "free deck was emtied too soon because there are too many debaters"
                    " or some have too many cards. Please re-initialize the game"
                )
                break
            else:
                # pop last card from a shuffled free deck
                given_card_unique_id = free_deck.pop()

                # get file_id which is used to send a sticker
                file_id = context.bot_data["deck_data"]["stickers"][
                    given_card_unique_id
                ]["file_id"]

                message: Message = await context.bot.send_sticker(
                    chat_id=values["chat_id"], sticker=file_id
                )

                # add this unique_id and it's message_id to debater's hand
                context.bot_data[_DEBATERS_DICT_KEY][player]["hand"].update(
                    {given_card_unique_id: message.id}
                )


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.bot_data["is_game_started"]:
        update.message.reply_text("Game already in progress")
    else:
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
    When he wants to use some card, he should send the same card from his sticker pack.
    This card will then be added to active cards. If he wants to use another card,
    he would need to send another sticker.
    Old one will be deleted, to keep things less cluttered.

    Guesser: after sending a sticker user think some debater has used,
    the keyboard is sent to ask, if user really meant to use this sticker.
    After confirmation, the global check is initiated in a function guess_buttons.
    """
    data: constants.BotData = context.bot_data
    if data["is_game_started"]:
        # if user is a debater
        if update.effective_user.id in data[_DEBATERS_DICT_KEY]:
            if (
                update.effective_message.sticker.file_unique_id
                in data[_DEBATERS_DICT_KEY]["hand"]
            ):
                # add matched sticker to active cards
                data["active_cards"].add(
                    update.effective_message.sticker.file_unique_id
                )
            else:
                text_message: Message = update.effective_user.send_message(
                    "You don't have this sticker in your hand."
                    "\n(Message and sticker above will be deleted in 7 seconds)"
                )
                sleep(7)
                update.effective_message.delete()
                text_message.delete()

        # if user is a guesser
        elif update.effective_user.id in data[_GUESSERS_DICT_KEY]:
            keyboard = [
                InlineKeyboardButton("Yes", callback_data=f"guess-yes"),
                InlineKeyboardButton("No", callback_data=f"guess-no"),
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "You want to try to guess this card?:", reply_markup=reply_markup
            )
        else:
            update.effective_user.send_message(
                "Sorry, you don't have a role in active game."
            )
    else:
        update.effective_user.send_message("Sorry, the game hasn't started yet.")


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

    # initialize storage dicts
    data: constants.BotData = {
        _DEBATERS_DICT_KEY: {},
        _GUESSERS_DICT_KEY: {},
        "admin": {},
        "free_deck": [],  # [file_unique_id, ... file_unique_id]
        "is_game_started": False,
        "deck_data": entities.get_deck(),  # load deck so bot could
        # send stickers by their id
        "active_cards": {},
    }
    application.bot_data = data

    # choose a role when entering the room
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start_buttons, pattern="^start-"))

    # basic game start conditions, progress and end conditions
    application.add_handler(CommandHandler("help", help))

    # TODO: add admin function to clear all users roles,
    # e.g. if there is too much debaters

    # during game users mostly interact by first sending card to a bot
    application.add_handler(MessageHandler(filters.Sticker.ALL, guess))
    application.add_handler(CallbackQueryHandler(guess_buttons, pattern="^guess-"))

    # admin fucntion: start game with all conditions (i.e. score, hands and message)
    application.add_handler(CommandHandler("start_game", start_game))

    # admin function: end game, sending game results to all users
    application.add_handler(CommandHandler("end_game", end_game))

    application.run_polling()


if __name__ == "__main__":
    main()
