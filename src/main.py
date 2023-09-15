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
# TODO: add more informative help message
_HELP_TEXT = (
    "there should be some help, but have these at least:",
    " http://fallacymania.com/game",
)

_CARDS_PER_HAND = 5
_DEBATERS_DICT_KEY = constants.DEBATERS_DICT_KEY
_GUESSERS_DICT_KEY = constants.GUESSERS_DICT_KEY
_PDF_CARDS_PATH = constants.PDF_CARDS_PATH


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
        await update.effective_user.send_message(
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
            text=(
                "When saying a statement, use deck's stickerpack to activate a card."
                " You make a card active by sending it as a sticker."
            ),
        )
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
        await update.message.reply_text("Game already in progress")
    else:
        context.bot_data["is_game_started"] = True
        # use a function to generate hands for debaters
        await generate_hands(update, context)

        # TODO: unhardcode starter attempts
        # (should be a function based on rules and number of guessers)
        for player in context.bot_data[_GUESSERS_DICT_KEY]:
            context.bot_data[_GUESSERS_DICT_KEY][player]["points"]["score"] = 0
            context.bot_data[_GUESSERS_DICT_KEY][player]["points"]["attempts"] = 15

            await context.bot.send_message(
                chat_id=context.bot_data[_GUESSERS_DICT_KEY][player]["chat_id"],
                text=(
                    "Game started. Send cards you want to guess, then you'll"
                    " be able to pick a debater."
                ),
            )


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
    debaters: constants.BotData = context.bot_data[_DEBATERS_DICT_KEY]
    if context.bot_data["is_game_started"]:
        # if user is a debater
        if update.effective_user.id in debaters:
            if (
                update.effective_message.sticker.file_unique_id
                in debaters[update.effective_user.id]["hand"]
            ):
                sticker_id = update.effective_message.sticker.file_unique_id
                # add matched sticker to active cards
                context.bot_data["active_cards"].update(
                    {sticker_id: update.effective_user.id}
                )
                text_message = await update.effective_user.send_message(
                    (
                        "Card above is now active. Users may try to guess it."
                        "\nIf someone guesses correctly, you will get a new card."
                        "\n(If you said another statement, just send a new sticker"
                        " to change the active card.)"
                    )
                )

                debater_id = update.effective_user.id
                msg = context.bot_data["temp_msg"].get(debater_id)
                sticker_msg = None
                text_msg = None
                if msg:
                    sticker_msg = msg.get("sticker_id")
                    text_msg = msg.get("text_id")

                # if old active_card is present, delete them to keep hand uncluttered
                if sticker_msg:
                    sleep(0.5)
                    await context.bot.delete_message(
                        update.effective_chat.id, sticker_msg
                    )
                if text_msg:
                    sleep(0.5)
                    await context.bot.delete_message(update.effective_chat.id, text_msg)

                context.bot_data["temp_msg"].update(
                    {
                        debater_id: {
                            "sticker_id": update.effective_message.id,
                            "text_id": text_message.id,
                        }
                    }
                )

            else:
                # text_message: Message = await update.effective_user.send_message(
                #     "You don't have this card in your hand."
                #     "\n(Message and sticker above will be deleted in 5 seconds)"
                # )
                # sleep(5)
                await update.effective_message.delete()
                # await text_message.delete()

        # if user is a guesser
        elif update.effective_user.id in context.bot_data[_GUESSERS_DICT_KEY]:
            sticker_id = update.effective_message.sticker.file_unique_id
            context.user_data["card_for_global_check"] = sticker_id

            keyboard = [
                [
                    InlineKeyboardButton("Yes", callback_data="guess-yes"),
                    InlineKeyboardButton("No", callback_data="guess-no"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "You want to try to guess this card?:", reply_markup=reply_markup
            )
        else:
            await update.effective_user.send_message(
                "Sorry, you don't have a role in active game."
            )
    else:
        await update.effective_user.send_message("Sorry, the game hasn't started yet.")


async def update_hand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sticker_id = context.user_data["card_for_global_check"]
    bot_data: constants.BotData = context.bot_data
    debater_id = bot_data["active_cards"][sticker_id]
    debater_chat_id = bot_data[_DEBATERS_DICT_KEY][debater_id]["chat_id"]

    # pop guessed sticker from debater's dict hand
    message_id = bot_data[_DEBATERS_DICT_KEY][debater_id]["hand"].pop(sticker_id)

    # delete guessed sticker in debater's telegram conversation hand
    await context.bot.delete_message(debater_id, message_id)

    # get new card from a free deck
    new_card = context.bot_data["free_deck"].pop()

    # clear old debater's active card messages
    msg = context.bot_data["temp_msg"].get(debater_id)
    sticker_msg = None
    text_msg = None
    if msg:
        sticker_msg = msg.get("sticker_id")
        text_msg = msg.get("text_id")
    if sticker_msg:
        sleep(0.5)
        await context.bot.delete_message(debater_chat_id, sticker_msg)
    if text_msg:
        sleep(0.5)
        await context.bot.delete_message(debater_chat_id, text_msg)
    context.bot_data["temp_msg"].update(
        {debater_id: {"sticker_id": None, "text_id": None}}
    )
    # get file_id which is used to send a sticker
    file_id = bot_data["deck_data"]["stickers"][new_card]["file_id"]

    # send this sticker to the debater
    message: Message = await context.bot.send_sticker(
        chat_id=debater_chat_id, sticker=file_id
    )

    # add this card's unique_id to debater's dict hand
    bot_data[_DEBATERS_DICT_KEY][debater_id]["hand"].update({new_card: message.id})


async def global_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        sticker_id = context.user_data["card_for_global_check"]
    except KeyError:
        await update.effective_user.send_message(
            "Sorry, for some reason bot hasn't saved a sticker in his memory."
        )
    my_points = context.bot_data["guesser"][update.effective_user.id]["points"]
    if sticker_id in context.bot_data["active_cards"]:
        await update.effective_user.send_message("You got it right and got a point!")
        my_points["score"] += 1
        await update_hand(update, context)
    else:
        if my_points["attempts"] > 0:
            my_points["attempts"] -= 1

            attempts = my_points["attempts"]
            await update.effective_user.send_message(
                f"You haven't guessed correctly and spent one attempt ({attempts} left)"
            )
            if my_points["attempts"] == 0:
                await update.effective_user.send_message(
                    "You spent all your attempts."
                    " From now on, every wrong guess will take away one point."
                )
        else:
            await update.effective_user.send_message("You lost a point, be careful.")


async def guess_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Parses the CallbackQuery sent by guesser from 'guess' function.
    Initializes a global check of cards. If card sent by the guesser matches
    any of active card from debaters, guesser gets a point.
    If it doesn't match, guesser loses one 'attempt' (until reaches zero).
    If he has no attempts left, the point is taken from him (can go negative).
    """
    query = update.callback_query
    await query.answer()

    if query.data == "guess-yes":
        await update.effective_user.send_message("Checking your answer...")
        # hardcoded value to make an illusion of thoughtful checking
        sleep(1)
        await global_check(update, context)

    elif query.data == "guess-no":
        await query.edit_message_text(
            text="This sticker will not be sent. You can continue by sending another."
        )
    else:
        await query.edit_message_text(text="Something went wrong with CallbackQuery.")


async def end_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # TODO: broadcast game results to all users
    # TODO: save how many times each debater was correctly guessed
    pass


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = "".join(_HELP_TEXT)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)


async def players(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """list all users in a group and their roles"""
    guesser: constants.Guesser
    debater: constants.Debater
    info = []
    for user_id, debater in context.bot_data[_DEBATERS_DICT_KEY].items():
        info.append(f'{debater["full_name"]} (@{debater["username"]}): {_DEBATER_NAME}')

    for user_id, guesser in context.bot_data[_GUESSERS_DICT_KEY].items():
        info.append(f'{guesser["full_name"]}: (@{guesser["username"]}){_GUESSER_NAME}')

    text = "\n".join(info)

    await update.effective_chat.send_message(text=text)


async def file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """send a message with a PDF file containing cards"""
    await update.effective_chat.send_document(document=open(_PDF_CARDS_PATH, "rb"))


async def stickerpack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """send message with first sticker from a deck's stickerpack"""
    file_id = context.bot_data["deck_data"]["stickers"]["AgADAQADndpmHQ"]["file_id"]
    await update.message.reply_sticker(file_id)


async def hand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # TODO: resend messages with your active hand (if you're a debater)
    pass
    # if context.bot_data["is_game_started"]:
    #     user_id = update.effective_user.id
    #     debater: constants.Debater = context.bot_data[_DEBATERS_DICT_KEY].get(user_id)

    #     if debater is not None:
    #         await update.message.reply_text(
    #             text=f"Your hand have these {_CARDS_PER_HAND} cards:"
    #         )
    #         for sticker_id, message_id in debater["hand"]:
    #             message: Message = await context.bot.send_sticker(
    #                 chat_id=values["chat_id"], sticker=context.bot_data.deck_data
    #             )
    #     else:
    #         await update.effective_user.send_message(
    #             "Sorry, you are not a debater and can't use this command."
    #         )
    # else:
    #     await update.effective_user.send_message("Sorry, the game hasn't started yet.")


async def score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # TODO: get a message with your points and left attempts (if you're a guesser)
    pass


def main() -> None:
    application = ApplicationBuilder().token(get_token()).build()

    # initialize storage dicts
    data: constants.BotData = {
        _DEBATERS_DICT_KEY: {},
        _GUESSERS_DICT_KEY: {},
        "admin": dict(),
        "is_game_started": False,
        "active_cards": dict(),
        # [file_unique_id, ... file_unique_id]
        "free_deck": list(),
        # load deck so bot could send stickers by their id
        "deck_data": entities.get_deck(),
        # user_id: {sticker_id: msg_id, text_id: msg_id}
        # "temp_msg": dict[int, dict[str, int]],
        "temp_msg": dict(),
    }
    application.bot_data = data

    # choose a role when entering the room
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start_buttons, pattern="^start-"))

    # basic game start conditions, progress and end conditions
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("players", players))
    application.add_handler(CommandHandler("file", file))
    application.add_handler(CommandHandler("stickerpack", stickerpack))
    application.add_handler(CommandHandler("hand", hand))
    application.add_handler(CommandHandler("score", score))

    # TODO: add admin function to clear all users roles,
    # e.g. if there is too much debaters (or just use end_game, which
    # will have different logic based on is_game_started)

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
