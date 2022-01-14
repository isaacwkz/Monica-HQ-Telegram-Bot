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

################################################# Add Gift Idea Conversation Handler #################################################

GIFT_IDEA, GIFT_IDEA_END = range(2)

# /addgiftidea command callback
# This gets a full list of contacts then asks for the contact ID for the note to be added to
def addgiftidea_cb(update: Update, context: CallbackContext) -> int:
    # Loggggg
    logging.info(str(update.message.chat.username) + " is adding a gift idea")
    update.message.reply_text(text="Adding a gift idea for someone?")
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
    update.message.reply_text(text="Let me know the ID of the contact you want to add a gift idea for!")
    # Proceed to next state and wait for user input
    return GIFT_IDEA

# We got the contact ID to add reminders for
# We will store this in the persistent context then ask for the body of the note
def addgiftidea_comments_cb(update: Update, context: CallbackContext) -> int:
    # Get contact ID
    note_contact_id = int(update.message.text)
    # Store this in persistent context
    context.user_data['giftidea_contact_id'] = note_contact_id
    # Retrieves contact list from persistent context
    contacts = context.user_data['contacts_dict']
    # Tries to find the name of the contact from the list of dict
    contact_name = next((item for item in contacts if item["id"] == note_contact_id), None)
    
    if contact_name is None:
        update.message.reply_text(text="Oops I can\'t find that contact, please try again!")
        logging.info(str(update.message.chat.username) + " Bruh, invalid ID of " + str(note_contact_id))
        return ConversationHandler.END
    contact_name = contact_name['name']
    update.message.reply_text(text="I\'ll add a gift idea for " + contact_name)
    context.user_data['giftidea_contact_name'] = contact_name
    logging.info(str(update.message.chat.username) + " adding gift idea for ID: " + str(note_contact_id) + " Name: " + contact_name)

    update.message.reply_text(text="And what is the gift idea?")
    return GIFT_IDEA_END

def addgiftidea_done_cb(update: Update, context: CallbackContext) -> int:
    gift_idea = str(update.message.text)
    contact_id = context.user_data['giftidea_contact_id']
    gift_idea_dict = {"contact_id": str(contact_id),
                      "name": gift_idea,
                      "status": "idea"}
    response = MonicaAPI.post_gift(gift_idea_dict)
    logging.info(str(update.message.chat.username) + " trigger an event : " + str(response))
    update.message.reply_text('All done!')
    context.user_data.clear()
    return ConversationHandler.END
    
def addgiftidea_cancel_cb(update: Update, context: CallbackContext) -> int:
    #Cancels and ends the conversation.
    user = update.message.from_user
    logging.info(str(update.message.chat.username) + " cancelled adding the reminder")
    update.message.reply_text('Oh.. Okay!')
    context.user_data.clear()
    return ConversationHandler.END

################################################# Get Gift Idea for Contact #################################################

GET_GIFTIDEA_CONTACT = 1

# /getgiftidea command callback
# This gets a full list of contacts then asks for the contact ID for the note to be added to
def getgiftidea_cb(update: Update, context: CallbackContext) -> int:
    # Loggggg
    logging.info(str(update.message.chat.username) + " is getting a gift idea")
    update.message.reply_text(text="Want to retrieve a gift idea?")
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
    message = ("Let me know the ID of the contact you want to get gift ideas for!\n" +
               "You can also enter __all__ to retrieve gift ideas for all contacts")
    update.message.reply_text(text="Let me know the ID of the contact you want to get gift ideas for!")
    # Proceed to next state and wait for user input
    return GET_GIFTIDEA_CONTACT

def getgiftidea_contact_id_cb(update: Update, context: CallbackContext) -> int:
    # Get contact ID
    if str(update.message.text).lower() == "all":
        # Get all gifts
        update.message.reply_text(text="Getting all gift ideas!\nHold on...")
        contact_dict = context.user_data['contacts_dict']
        message = ""
        for contact in contact_dict:
            contact_id = contact['id']
            gift_list = MonicaAPI.get_gifts(contact_id)
            if gift_list:
                message = message + "Gifts for " + str(gift_list[0]['contact_name']) + "!\n"
                for gift in gift_list:
                    message = (message + str(gift['name']) + "\n" +
                                        "Status: " + str(gift['status']) + "\n" +
                                        "Updated on: " + str(gift['updated_at'].date()) + "\n\n")
                message = message + "\n"
        if message:
            update.message.reply_text(text=message)
        else:
            update.message.reply_text(text="You have no gift ideas currently!")
        context.user_data.clear()
        return ConversationHandler.END
    try:
        giftidea_contact_id = int(update.message.text)
    except:
        update.message.reply_text(text="Are you sure that\'s a number?\nPlease try again!")
        return GET_GIFTIDEA_CONTACT

    # Store this in persistent context
    context.user_data['giftidea_contact_id'] = giftidea_contact_id
    # Retrieves contact list from persistent context
    contacts = context.user_data['contacts_dict']
    # Tries to find the name of the contact from the list of dict
    contact_name = next((item for item in contacts if item["id"] == giftidea_contact_id), None)
    
    if contact_name is None:
        update.message.reply_text(text="Oops I can\'t find that contact, please try again!")
        logging.info(str(update.message.chat.username) + " Bruh, invalid ID of " + str(giftidea_contact_id))
        return ConversationHandler.END
    update.message.reply_text(text="I\'ll get gift ideas for " + str(contact_name["name"]))
    logging.info(str(update.message.chat.username) + " is getting gift ideas for " + str(contact_name["name"]))
    gift_dict = MonicaAPI.get_gifts(giftidea_contact_id)
    if not gift_dict:
        update.message.reply_text(text="There is no gift ideas for " + str(contact_name["name"]) + "!")
    else:
        message = "Gift ideas for " + str(contact_name["name"]) + "!\n"
        for gift in gift_dict:
            message = (message + gift['name'] + "\n" + 
                       "Status: " + gift['status'] + "\n" +
                       "Updated on: " + str(gift['updated_at'].date()) + "\n\n")
        update.message.reply_text(text=message)
    context.user_data.clear()
    return ConversationHandler.END

def getgiftidea_cancel_cb(update: Update, context: CallbackContext) -> int:
    #Cancels and ends the conversation.
    user = update.message.from_user
    logging.info(str(update.message.chat.username) + " cancelled adding the reminder")
    update.message.reply_text('Oh.. Okay!')
    context.user_data.clear()
    return ConversationHandler.END