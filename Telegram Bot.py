######### System Imports #########
import logging
from datetime import datetime, tzinfo, time
import pytz
from calendar import monthrange
######### Telegram Imports #########
from telegram import ReplyKeyboardMarkup, message
from telegram import ReplyKeyboardRemove
from telegram import InlineKeyboardMarkup
from telegram import Update
from telegram.ext import Updater
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import MessageFilter
from telegram.ext import ConversationHandler
from telegram.ext import CallbackQueryHandler
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
######### Other Imports #########
import requests
######### Custom User Imports #########
import MonicaAPI
import TeleAddReminders
import TeleNotes
import TelePushNotifications
import TeleAddContact
import TeleGifts

#logging.basicConfig(filename='runtime.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
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

updater = Updater(token=_telegram_api_token, use_context=True)
dispatcher = updater.dispatcher

################################################# Custom filters below #################################################

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
        word_list = ["command list","cmd list","cmd","commands"]
        for word in word_list:
            if str(message.text).lower() == word:
                return True
        return False
# Initialize the class.
filter_command_list = FilterCommandList()

# Custom message filter to cancel current command
# This function returns a false when "cancel" is found
# This causes ConversationHandler to move into it fallback handler
# This assumes that regex is used as filter
class FilterCancelWord(MessageFilter):
    def filter(self, message):
        word_list = ["cancel"]
        for word in word_list:
            if str(message.text).lower() == word:
                return False
        return True
# Initialize the class.
filter_cancel_command = FilterCancelWord()

################################################# Command handlers below #################################################

########################################################################################
# /start command handler
def start_cb(update: Update, context: CallbackContext):
    logging.info(str(update.message.chat.username) + " started the BOT")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hi there, " + str(update.message.chat.username) + "!~")
# Add /start command callback to command queue
start_handler = CommandHandler('start', start_cb, filters=filter_userid)
dispatcher.add_handler(start_handler)

########################################################################################
# /notify and /stop_notification command handler
notification_handler = CommandHandler('notify', TelePushNotifications.start_notification_cb, filters=filter_userid)
stop_notification_handler = CommandHandler('stop_notification', TelePushNotifications.stop_notifications_cb, filters=filter_userid)
dispatcher.add_handler(notification_handler)
dispatcher.add_handler(stop_notification_handler)

########################################################################################
# /getreminders command handler
def reminders_cb(update: Update, context: CallbackContext):
    days_to_check = 0
    # Hacky way to get a param from user
    # TODO maybe?
    try:
        days_to_check = int(context.args[0])
    # If no param is supplied we skip
    except (IndexError, ValueError):
        pass
    logging.info(str(update.message.chat.username) + " is checking for reminders")
    if days_to_check:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Reminders for the next " + str(days_to_check) + " days!")
        reminders = MonicaAPI.get_reminders(days_to_check)
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(reminders))
    else:
    # Get reminders for this month
        context.bot.send_message(chat_id=update.effective_chat.id, text="Reminders for the month!")
        today = datetime.now().day
        year = datetime.now().year
        month = datetime.now().month
        num_days = monthrange(year, month)[1]
        reminders = MonicaAPI.get_reminders(num_days-today)
        context.bot.send_message(chat_id=update.effective_chat.id, text=str(reminders))
# Add /reminders command callback to command queue
reminders_handler = CommandHandler('getreminders', reminders_cb, filters=filter_userid)
dispatcher.add_handler(reminders_handler)

########################################################################################
# /ipaddress command handler
def get_ip_address_cb(update: Update, context: CallbackContext):
    logging.info(str(update.message.chat.username) + " is checking the external IP address")
    r=requests.get(url="http://api.ipify.org/")
    ip = r.text
    update.message.reply_text(text="My IP address is " + str(ip))
    logging.info("Current IP - " + str(ip))
# Add /ipaddress command callback to command queue
ip_address_handler = CommandHandler('ipaddress', get_ip_address_cb, filters=filter_userid)
dispatcher.add_handler(ip_address_handler)

################################################# Add Reminder Conversation Handler #################################################
# This was placed in a seperate file to keep this somewhat clean
# Add conversation handler with the states
# TODO huh... the /cancel command doesnt work when handler is expecting a text
add_reminder_handler = ConversationHandler( entry_points=[CommandHandler('addreminders', TeleAddReminders.addreminders_cb, filters=filter_userid)],
                                            states={TeleAddReminders.RM_CONTACT_ID: [MessageHandler(Filters.regex('^\d+$') & filter_userid, TeleAddReminders.addreminders_contact_id_cb)],
                                                    TeleAddReminders.RM_TITLE: [MessageHandler(filter_userid & Filters.text, TeleAddReminders.addreminders_title_cb)],
                                                    TeleAddReminders.RM_DESCRIPTION: [MessageHandler(filter_userid & Filters.text, TeleAddReminders.addreminders_description_cb)],
                                                    TeleAddReminders.RM_CALENDAR: [CallbackQueryHandler(TeleAddReminders.addreminders_calendar_cb)],
                                                    TeleAddReminders.RM_FREQ_TYPE: [MessageHandler(filter_userid, TeleAddReminders.addreminders_freq_type_cb)],
                                                    TeleAddReminders.RM_FREQ: [MessageHandler(Filters.regex('^\d+$') & filter_userid, TeleAddReminders.addreminders_freq_period_cb)]},
                                            fallbacks=[CommandHandler('cancel', TeleAddReminders.addreminders_cancel_cb, filters=filter_userid)],)
# Add to scheduler
dispatcher.add_handler(add_reminder_handler)

################################################# Add Contact Conversation Handler #################################################

add_contacts_handler = ConversationHandler(entry_points=[CommandHandler('addcontact', TeleAddContact.addcontact_cb, filters=filter_userid)],
                                        states={TeleAddContact.CONTACT_NICKNAME: [MessageHandler(Filters.text & filter_userid, TeleAddContact.addcontact_nickname_cb)],
                                                TeleAddContact.CONTACT_GENDER: [MessageHandler(filter_userid & Filters.text, TeleAddContact.addcontact_gender_cb)],
                                                TeleAddContact.CONTACT_BIRTHDAY: [MessageHandler(filter_userid & Filters.text, TeleAddContact.addcontact_birthday_cb)],
                                                TeleAddContact.CONTACT_BD_CALENDAR: [MessageHandler(filter_userid & Filters.text, TeleAddContact.addcontact_calendar_cb)],
                                                TeleAddContact.CONTACT_BD_CL_UPDATE: [CallbackQueryHandler(TeleAddContact.addcontact_cl_update_cb)]},
                                        fallbacks=[CommandHandler('cancel', TeleAddContact.addcontact_cancel_cb, filters=filter_userid)],)
# Add to scheduler
dispatcher.add_handler(add_contacts_handler)

################################################# Get Gift Idea for Contact #################################################

get_notes_handler = ConversationHandler(entry_points=[CommandHandler('getgiftidea', TeleGifts.getgiftidea_cb, filters=filter_userid)],
                                        states={TeleGifts.GET_GIFTIDEA_CONTACT: [MessageHandler(filter_userid, TeleGifts.getgiftidea_contact_id_cb)]},
                                        fallbacks=[CommandHandler('cancel', TeleGifts.getgiftidea_cancel_cb, filters=filter_userid)],)
# Add to scheduler
dispatcher.add_handler(get_notes_handler)

################################################# Add Gift Idea Conversation Handler #################################################

add_gift_idea_handler = ConversationHandler(entry_points=[CommandHandler('addgiftidea', TeleGifts.addgiftidea_cb, filters=filter_userid)],
                                            states={TeleGifts.GIFT_IDEA: [MessageHandler(Filters.regex('^\d+$') & filter_userid, TeleGifts.addgiftidea_comments_cb)],
                                                    TeleGifts.GIFT_IDEA_END: [MessageHandler(filter_userid & Filters.text, TeleGifts.addgiftidea_done_cb)]},
                                            fallbacks=[CommandHandler('cancel', TeleGifts.addgiftidea_cancel_cb, filters=filter_userid)],)
# Add to scheduler
dispatcher.add_handler(add_gift_idea_handler)

################################################# Add Notes Conversation Handler #################################################

add_notes_handler = ConversationHandler(entry_points=[CommandHandler('addnotes', TeleNotes.addnotes_cb, filters=filter_userid)],
                                        states={TeleNotes.NOTES_TITLE: [MessageHandler(Filters.regex('^\d+$') & filter_userid, TeleNotes.addnotes_contact_id_cb)],
                                                TeleNotes.NOTES_FAV: [MessageHandler(filter_userid & Filters.text, TeleNotes.addnotes_body_cb)],
                                                TeleNotes.NOTES_DONE: [MessageHandler(filter_userid & Filters.text, TeleNotes.addnotes_fav_done_cb)]},
                                        fallbacks=[CommandHandler('cancel', TeleNotes.addnotes_cancel_cb, filters=filter_userid)],)
# Add to scheduler
dispatcher.add_handler(add_notes_handler)

################################################# Get Notes for Contact #################################################

get_notes_handler = ConversationHandler(entry_points=[CommandHandler('getnotes', TeleNotes.getnotes_cb, filters=filter_userid)],
                                        states={TeleNotes.GET_NOTES_CONTACT: [MessageHandler(Filters.regex('^\d+$') & filter_userid, TeleNotes.getnotes_contact_id_cb)]},
                                        fallbacks=[CommandHandler('cancel', TeleNotes.getnotes_cancel_cb, filters=filter_userid)],)
# Add to scheduler
dispatcher.add_handler(get_notes_handler)

################################################# Message handlers below #################################################

def command_list_cb(update: Update, context: CallbackContext):
    command_list = ("/start  | ping/echoes back username\n" +
                    "--------------------- Monica ---------------------\n"
                    "/getreminders (int)  | gets reminders for number of days - if no param, gets for 1 month\n" +
                    "/addreminders  | adds a new reminder\n" +
                    "/addnotes  | adds notes to a contact\n" +
                    "/getnotes  | gets notes for a contact\n" +
                    "/addgiftidea  | adds gift ideas for a contact\n" +
                    "/getgiftidea  | retrieves gift ideas for specific or all contacts\n" +
                    "/addcontact  | adds a new contact\n" +
                    "/notify  | sends notifications\n" +
                    "/stop_notification  | stops notifications\n" + 
                    ############## Others ###################
                    "--------------------------------------------------\n" +
                    "/ipaddress  | gets current IP of bot")
    context.bot.send_message(chat_id=update.effective_chat.id, text=command_list)

command_list_handler = MessageHandler(filter_userid & filter_command_list, command_list_cb)
dispatcher.add_handler(command_list_handler)

def exception_catcher_cb(update: Update, context: CallbackContext):
    logging.info("Message from " + str(update.message.chat.username) + ": " + str(update.message.text))
    message = "Sorry I didn't understand that.."
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)

################################################# Hard error handler #################################################
def error_handler(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Ooops.. Something broke..")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Clearing persistent user data")
    context.user_data.clear()

#dispatcher.add_error_handler(error_handler)

exception_catcher_handler = MessageHandler(filter_userid & ~filter_command_list, exception_catcher_cb)
dispatcher.add_handler(exception_catcher_handler)

updater.start_polling()
updater.idle()