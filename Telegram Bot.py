import logging
from telegram.ext import Updater
from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import MessageFilter
import MonicaAPI

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

token_file = open('telegram api token.txt', 'r')
for token in token_file:
    _telegram_api_token = token.rstrip('\0')
token_file.close()

# Tho the filename might imply that there can be more than one telegram username accepted
# The script practically accepts only one username.. No I dont intend to fix this either
username_file = open('telegram accepted username.txt', 'r')
for username in username_file:
    telegram_username = username.rstrip('\0')
username_file.close()

####################### Custom filters below #######################

# Custom message filter for userid
class FilterUserID(MessageFilter):
    def filter(self, message):
        if telegram_username not in message.chat.username:
            logging.warning("Message from " + str(message.chat.username) + ": " + str(message.text))
        return telegram_username in message.chat.username
# Initialize the class.
filter_userid = FilterUserID()

# Custom message filter to get command list
class FilterCommandList(MessageFilter):
    def filter(self, message):
        return 'command list' in str(message.text).lower()
# Initialize the class.
filter_command_list = FilterCommandList()

updater = Updater(token=_telegram_api_token, use_context=True)
dispatcher = updater.dispatcher


####################### Command handlers below #######################

# /start command callback
def start_cb(update: Update, context: CallbackContext):
    logging.info(str(update.message.chat.username) + " started the BOT")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hi there, " + str(update.message.chat.username) + "!~")
# Add /start command callback to command queue
start_handler = CommandHandler('start', start_cb, filters=filter_userid)
dispatcher.add_handler(start_handler)


# /reminders command callback
def reminders_cb(update: Update, context: CallbackContext):
    logging.info(str(update.message.chat.username) + " checked for reminders")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Reminders for the month!")
    reminders = MonicaAPI.get_reminders()
    context.bot.send_message(chat_id=update.effective_chat.id, text=str(reminders))

# Add /reminders command callback to command queue
reminders_handler = CommandHandler('reminders', reminders_cb, filters=filter_userid)
dispatcher.add_handler(reminders_handler)

# /reminders command callback
def add_reminders_cb(update: Update, context: CallbackContext):
    logging.info(str(update.message.chat.username) + "is adding a reminder")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Adding a reminder?")

# Add /reminders command callback to command queue
add_reminders_handler = CommandHandler('addreminders', add_reminders_cb, filters=filter_userid)
dispatcher.add_handler(add_reminders_handler)


####################### Message handlers below #######################

def command_list_cb(update: Update, context: CallbackContext):
    command_list = "/reminders\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=command_list)

command_list_handler = MessageHandler(filter_userid & filter_command_list, command_list_cb)
dispatcher.add_handler(command_list_handler)

def exception_catcher_cb(update: Update, context: CallbackContext):
    logging.info("Message from " + str(update.message.chat.username) + ": " + str(update.message.text))
    message = "Sorry I didn't understand that.."
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

exception_catcher_handler = MessageHandler(filter_userid & ~filter_command_list, exception_catcher_cb)
dispatcher.add_handler(exception_catcher_handler)

updater.start_polling()