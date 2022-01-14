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

# Adding contacts
# 1. Get first name
# 2. Get nickname (if any)
# 3. Get gender
# 4. Get is birthday known?
    # 4.1 Open calender
    # 4.2 Update calender
    # 4.2.1 If birthday year is current year, birth year is unknown

CONTACT_NICKNAME, CONTACT_GENDER, CONTACT_BIRTHDAY, CONTACT_BD_CALENDAR, CONTACT_BD_CL_UPDATE = range(5)

# /addcontact cb
def addcontact_cb(update: Update, context: CallbackContext) -> int:
    # Loggggg
    logging.info(str(update.message.chat.username) + " is adding a contact")
    update.message.reply_text(text="Adding a new contact?")
    update.message.reply_text(text="What is the name of the contact?\nYou can type /cancel to cancel this action anytime")
    return CONTACT_NICKNAME

# Get nickname
def addcontact_nickname_cb(update: Update, context: CallbackContext) -> int:
    contact_name = str(update.message.text)
    context.user_data['first_name'] = contact_name
    # Loggggg
    logging.info(str(update.message.chat.username) + " contact name: " + contact_name)
    update.message.reply_text(text="And what is the nickname of the contact?\nYou can type __none__ if not applicable")
    return CONTACT_GENDER

# Get gender
def addcontact_gender_cb(update: Update, context: CallbackContext) -> int:
    contact_nickname = str(update.message.text)
    if contact_nickname.lower() != "none":
        context.user_data['nickname'] = contact_nickname
    else:
        context.user_data['nickname'] = "None"
    message_gender = "Got it!\nWhat is the gender of " + context.user_data['first_name'] + "?"
    gender_dict = MonicaAPI.get_gender_id()
    context.user_data['gender_dict'] = gender_dict
    gender_list = []
    for gender in gender_dict:
        gender_list.append(gender['name'])
    context.bot.send_message(chat_id=update.effective_chat.id, text=message_gender,
                            reply_markup=ReplyKeyboardMarkup([gender_list], resize_keyboard=True, one_time_keyboard=True))
    return CONTACT_BIRTHDAY

# Get birthday
def addcontact_birthday_cb(update: Update, context: CallbackContext) -> int:
    gender = str(update.message.text)
    # Check if user keyed in a valid gender from the options   
    gender_dict = context.user_data['gender_dict']
    gender = next((i for i, item in enumerate(gender_dict) if item["name"] == gender), None)
    if gender == "None":
        logging.info(str(update.message.chat.username) + " keyed in an invalid option, " + str(gender))
        message_gender = "Sorry I didn\'t understand that, please chose one of the options below"
        gender_list = []
        for gender in gender_dict:
            gender_list.append(gender['name'])
        context.bot.send_message(chat_id=update.effective_chat.id, text=message_gender,
                            reply_markup=ReplyKeyboardMarkup([gender_list], resize_keyboard=True, one_time_keyboard=True))
        return CONTACT_BIRTHDAY
    # Fall through
    gender = gender_dict[gender]['id']
    context.user_data['gender_id'] = gender
    # Loggggg
    logging.info(str(update.message.chat.username) + " Selected gender ID " + str(gender))

    # Get birthday
    bday_message = "Do you know the birthday of the contact?"
    bday_question = [["I know only the dates", "I don't know the birthday"], ["I know both the birthday and year"]]
    context.user_data['bday_question'] = bday_question

    context.bot.send_message(chat_id=update.effective_chat.id, text=bday_message,
                             reply_markup=ReplyKeyboardMarkup(bday_question, resize_keyboard=True, one_time_keyboard=True))
    return CONTACT_BD_CALENDAR

def addcontact_calendar_cb(update: Update, context: CallbackContext) -> int:
    bday_answer = str(update.message.text)
    bday_keyboard = context.user_data['bday_question']
    bday_question = bday_keyboard[0] + bday_keyboard[1]
    if bday_answer not in bday_question:
        logging.info(str(update.message.chat.username) + " keyed in an invalid option - " + bday_answer)
        message_invalid = "Sorry I didn\'t understand that, please chose one of the options below"
        context.bot.send_message(chat_id=update.effective_chat.id, text=message_invalid,
                                 reply_markup=ReplyKeyboardMarkup(bday_keyboard, resize_keyboard=True, one_time_keyboard=True))
        return CONTACT_BD_CALENDAR

    # Fall through
    index = bday_question.index(bday_answer)
    context.user_data['bday_qusetion_index'] = index
    logging.info(str(update.message.chat.username) + " selected option :" + bday_answer + " index : " + str(index))

    # Know the date but not the year
    if index == 0:
        context.user_data['is_birthdate_known'] = 1
        message = "Select the date in the calendar below.\nYou may select " + str(datetime.now().year) + " for the year of birth"
        update.message.reply_text(text=message)
        calendar, step = DetailedTelegramCalendar().build()
        update.message.reply_text("Select " + LSTEP[step], reply_markup=calendar)
        return CONTACT_BD_CL_UPDATE

    # Don't know
    elif index == 1:
        update.message.reply_text(text="Got it!")
        # Build dict to pass to Monica
        contact_dict = {"first_name": context.user_data['first_name'],
                        "nickname": context.user_data['nickname'],
                        "gender_id": context.user_data['gender_id'],
                        "is_birthdate_known" : "0",
                        "is_partial": "0",
                        "is_deceased": "0",
                        "is_deceased_date_known": "0"}
        key_to_pop = []
        for key in contact_dict:
            if contact_dict[key] == "None":
                key_to_pop.append(key)
        for key in key_to_pop:
            contact_dict.pop(key)
        response = MonicaAPI.post_contact(contact_dict)
        logging.info(str(update.message.chat.username) + " trigger an event : " + str(response))

    # Know both date and year
    elif index ==  2:
        context.user_data['is_birthdate_known'] = 1
        message = "Select the date and year in the calendar below."
        update.message.reply_text(text=message)
        calendar, step = DetailedTelegramCalendar().build()
        update.message.reply_text("Select " + LSTEP[step], reply_markup=calendar)
        return CONTACT_BD_CL_UPDATE

    else:
        logging.info(str(update.message.chat.username) + " invalid index when adding contacts: " + str(index))
        update.message.reply_text(text="Oops.. Something went wrong..\nCancelling action...")
        context.user_data.clear()
        return ConversationHandler.END

def addcontact_cl_update_cb(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    result, key, step = DetailedTelegramCalendar().process(query.data)
    if not result and key:
        query.edit_message_text(f"Select {LSTEP[step]}", reply_markup=key)
        return CONTACT_BD_CL_UPDATE
    elif result:
        query.delete_message()
        date = str(result)
        full_date = datetime.strptime(date, '%Y-%m-%d')
        day = full_date.day
        month = full_date.month
        year = full_date.year
        context.user_data['contact_birth_date'] = date
        context.bot.send_message(chat_id=update.effective_chat.id, text="I will also be reminding of their birthday")
        logging.info(str(query.message.chat.username) + " birthdate is set for " + str(full_date.date()))
        # User knows the year
        if context.user_data['bday_qusetion_index'] == 0:
            year = "None"
        # Build dict to pass to Monica
        contact_dict = {"first_name": context.user_data['first_name'],
                        "nickname": context.user_data['nickname'],
                        "gender_id": context.user_data['gender_id'],
                        "birthdate_day": day,
                        "birthdate_month": month,
                        "birthdate_year": year,
                        "is_birthdate_known" : "1",
                        "is_partial": "0",
                        "is_deceased": "0",
                        "is_deceased_date_known": "0"}
        # Check year exists and check nickname exists
        # Remove key pairs with value "None"
        key_to_pop = []
        for key in contact_dict:
            if contact_dict[key] == "None":
                key_to_pop.append(key)
        for key in key_to_pop:
            contact_dict.pop(key)
        response = MonicaAPI.post_contact(contact_dict)
        logging.info(str(update.message.chat.username) + " trigger an event : " + str(response))
        
        context.bot.send_message(chat_id=update.effective_chat.id, text="I have saved your contact!")
        context.user_data.clear()
        return ConversationHandler.END


def addcontact_cancel_cb(update: Update, context: CallbackContext) -> int:
    #Cancels and ends the conversation.
    user = update.message.from_user
    logging.info(str(update.message.chat.username) + " cancelled adding the reminder")
    update.message.reply_text('Oh.. Okay!')
    context.user_data.clear()
    return ConversationHandler.END