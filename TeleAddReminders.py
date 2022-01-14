######### System Imports #########
import logging
from datetime import datetime
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

#################################################### Add reminders conversation ####################################################
# Conversation states
# 1. we get contact ID
# 2. Then we get title of reminder
# 3. Then we get descritpion of reminder - with the option to skip
# 4. Then we get reminder date
# 5. Then we get reminder frequency type (monthly, daily etc)
# 6. If applicatble we get reminder period (1 2 3 4)
# 7. else we're done and POST this to Monica
RM_CONTACT_ID, RM_TITLE, RM_DESCRIPTION, RM_CALENDAR, RM_FREQ_TYPE, RM_FREQ = range(6)

# /addreminders command callback
def addreminders_cb(update: Update, context: CallbackContext) -> int:
    # Loggggg
    logging.info(str(update.message.chat.username) + " is adding a reminder")
    update.message.reply_text(text="Adding a reminder?")
    # Get list of contacts and associated ID then proceed to spit it out
    contacts = MonicaAPI.get_contacts()
    # Sort by alphebetical order of names
    contacts = sorted(contacts, key=lambda d: d['name']) 
    # We will store the contact list in the persistent context so we don't have to repeatedly get the contact list
    # !!This contact list should only be used for A conversation instance!!
    context.user_data['contacts_dict'] = contacts
    update.message.reply_text(text="Here\'s a list of contacts and their associated ID")
    message = ""
    # Turns Python dict into a nice human readable string
    for index, item in enumerate(contacts):
        message = message + str(contacts[index]["id"]) + ": " + str(contacts[index]["name"] + "\n")
    update.message.reply_text(text=message)
    update.message.reply_text(text="Let me know the ID of the contact you want to add a reminder for!")
    # Proceed to next state and wait for user input
    return RM_CONTACT_ID

# We got the contact ID to add reminders for
# We will store this in the persistent context then ask for the title of the reminder
def addreminders_contact_id_cb(update: Update, context: CallbackContext) -> int:
    # Get contact ID
    rm_contact_id = int(update.message.text)
    # Store this in persistent context
    context.user_data['rm_contact_id'] = rm_contact_id
    # Retrieves contact list from persistent context
    contacts = context.user_data['contacts_dict']
    # Tries to find the name of the contact from the list of dict
    contact_name = next((item for item in contacts if item["id"] == rm_contact_id), None)
    
    if contact_name is None:
        update.message.reply_text(text="Oops I can\'t find that contact, please try again!")
        logging.info(str(update.message.chat.username) + " Bruh, invalid ID of " + str(rm_contact_id))
        return ConversationHandler.END
    contact_name = contact_name['name']
    update.message.reply_text(text="I\'ll add a reminder for " + contact_name)
    context.user_data['rm_contact_name'] = contact_name
    #logging.info(str(update.message.chat.username) + " adding reminder for ID: " + str(rm_contact_id) + " Name: " + contact_name)

    update.message.reply_text(text="What shall I put as the title of the reminder?")
    return RM_TITLE

# Now that we have the title of the reminder
# We will ask for the description of the reminder
# If description is ```none``` we will skip to reminder date
def addreminders_title_cb(update: Update, context: CallbackContext) -> int:
    # Get contact ID
    rm_title = str(update.message.text)
    # Store this in persistent context
    context.user_data['rm_title'] = rm_title
    #logging.info(str(update.message.chat.username) + " adding reminder title: " + rm_title)
    update.message.reply_text(text="Got it, would you like a description for your reminder?")
    update.message.reply_text(text="You can type __none__ if you have no description")
    return RM_DESCRIPTION

# We have the description
# We will ask for the date of the reminder!
def addreminders_description_cb(update: Update, context: CallbackContext) -> int:
    # Get contact ID
    rm_description = str(update.message.text)
    if rm_description.lower() != "none":
        # Store this in persistent context
        context.user_data['rm_description'] = rm_description
        #logging.info(str(update.message.chat.username) + " has have a description")
    else:
        context.user_data['rm_description'] = ""
        #logging.info(str(update.message.chat.username) + " does not have a description")

    update.message.reply_text(text="When shall I remind you?")
    calendar, step = DetailedTelegramCalendar().build()
    update.message.reply_text(  "Select " + LSTEP[step],
                                reply_markup=calendar)
    return RM_CALENDAR

# This process both calendar updating and saving of date
# Once we got the dates we will move on to asking for frequency type
def addreminders_calendar_cb(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()
    result, key, step = DetailedTelegramCalendar().process(query.data)
    if not result and key:
        query.edit_message_text(f"Select {LSTEP[step]}", reply_markup=key)
        return RM_CALENDAR
    elif result:
        #query.edit_message_text(f"{result}")
        query.delete_message()
        date = str(result)
        date = datetime.strptime(date, '%Y-%m-%d')
        context.user_data['rm_date'] = date
        context.bot.send_message(chat_id=update.effective_chat.id, text="I will be reminding you on " + str(date.date()))
        #logging.info(str(query.message.chat.username) + " reminder is set for " + str(date.date()))

        message_freq_type = "How often do you want to repeat this reminder?"
        freq_type = [["yearly", "monthly"],["weekly", "none"]]
        context.bot.send_message(chat_id=update.effective_chat.id, text=message_freq_type,
                                    reply_markup=ReplyKeyboardMarkup(freq_type, resize_keyboard=True, one_time_keyboard=True))

        return RM_FREQ_TYPE

# Now we process the frequency type before asking for how frequent
def addreminders_freq_type_cb(update: Update, context: CallbackContext) -> int:
    freq_type = str(update.message.text)
    if freq_type == "yearly":
        context.user_data['rm_freq_type'] = "year"
    elif freq_type == "monthly":
        context.user_data['rm_freq_type'] = "month"
    elif freq_type == "weekly":
        context.user_data['rm_freq_type'] = "week"
    elif freq_type == "none":
        context.user_data['rm_freq_type'] = "one_time"
        data = context.user_data
        reminder_post = {'title':str(data['rm_title']),
                        'description':str(data['rm_description']),
                        'initial_date':str(data['rm_date'].date()),
                        'frequency_type':str(data['rm_freq_type']),
                        'frequency_number':"1",
                        'contact_id':str(data['rm_contact_id'])}
        logging.info(str(update.message.chat.username) + " is setting a reminder: " + str(reminder_post))
        response = MonicaAPI.post_reminders(reminder_post)
        logging.info(str(update.message.chat.username) + " trigger an event : " + str(response))
        update.message.reply_text(text="Done!")

        context.user_data.clear()
        return ConversationHandler.END

    else:
        message_freq_type = "How often do you want to repeat this reminder?"
        freq_type = [["yearly", "monthly"],["weekly", "none"]]
        update.message.reply_text(text=message_freq_type, reply_markup=
                                    ReplyKeyboardMarkup(freq_type, resize_keyboard=True, one_time_keyboard=True))
        return RM_FREQ_TYPE
    update.message.reply_text(text="How often do you want to repeat?")
    return RM_FREQ

def addreminders_freq_period_cb(update: Update, context: CallbackContext) -> int:
    rm_freq_period = int(update.message.text)
    context.user_data['rm_freq_period'] = rm_freq_period
    data = context.user_data
    reminder_post = {'title':str(data['rm_title']),
                    'description':str(data['rm_description']),
                    'initial_date':str(data['rm_date'].date()),
                    'frequency_type':str(data['rm_freq_type']),
                    'frequency_number':str(data['rm_freq_period']),
                    'contact_id':str(data['rm_contact_id'])}
    logging.info(str(update.message.chat.username) + " is setting a reminder: " + str(reminder_post))
    
    response = MonicaAPI.post_reminders(reminder_post)
    logging.info(str(update.message.chat.username) + " trigger an event : " + str(response))
    update.message.reply_text(text="Done!")

    context.user_data.clear()
    return ConversationHandler.END

def addreminders_cancel_cb(update: Update, context: CallbackContext) -> int:
    #Cancels and ends the conversation.
    user = update.message.from_user
    logging.info(str(update.message.chat.username) + " cancelled adding the reminder")
    update.message.reply_text('Oh.. Okay!')
    context.user_data.clear()
    return ConversationHandler.END