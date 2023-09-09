import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
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
        # user is already in average roles dict
        if update.effective_user.id in context.bot_data[key]:
            context.bot_data[key].pop(update.effective_user.id)

    # add him again with specified role
    context.bot_data[dict_key] = entities.entity_data(update)


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
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    user = update.effective_user
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


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = "".join(_HELP_TEXT)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)


def main() -> None:
    application = ApplicationBuilder().token(get_token()).build()

    # initialize player storage dicts
    application.bot_data["debater"] = {}
    application.bot_data["guesser"] = {}
    application.bot_data["admin"] = {}

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CallbackQueryHandler(start_buttons))

    application.run_polling()


if __name__ == "__main__":
    main()
