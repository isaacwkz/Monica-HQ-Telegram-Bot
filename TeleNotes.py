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

NOTES_TITLE, NOTES_FAV, NOTES_DONE = range(3)

# /addnotes command callback
# This gets a full list of contacts then asks for the contact ID for the note to be added to
def addnotes_cb(update: Update, context: CallbackContext) -> int:
    # Loggggg
    logging.info(str(update.message.chat.username) + " is adding a note")
    update.message.reply_text(text="Adding a note?")
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
    update.message.reply_text(text="Let me know the ID of the contact you want to add a note for!")
    # Proceed to next state and wait for user input
    return NOTES_TITLE

# We got the contact ID to add reminders for
# We will store this in the persistent context then ask for the body of the note
def addnotes_contact_id_cb(update: Update, context: CallbackContext) -> int:
    # Get contact ID
    note_contact_id = int(update.message.text)
    # Store this in persistent context
    context.user_data['note_contact_id'] = note_contact_id
    # Retrieves contact list from persistent context
    contacts = context.user_data['contacts_dict']
    # Tries to find the name of the contact from the list of dict
    contact_name = next((item for item in contacts if item["id"] == note_contact_id), None)
    
    if contact_name is None:
        update.message.reply_text(text="Oops I can\'t find that contact, please try again!")
        logging.info(str(update.message.chat.username) + " Bruh, invalid ID of " + str(note_contact_id))
        return ConversationHandler.END
    contact_name = contact_name['name']
    update.message.reply_text(text="I\'ll add a note for " + contact_name)
    context.user_data['note_contact_name'] = contact_name
    #logging.info(str(update.message.chat.username) + " adding reminder for ID: " + str(rm_contact_id) + " Name: " + contact_name)

    update.message.reply_text(text="What shall I put in the body of the note?")
    return NOTES_FAV

# Now that we have the body of the note
# We will ask whether user wants to favorite the note
def addnotes_body_cb(update: Update, context: CallbackContext) -> int:
    # Get text
    note_body = str(update.message.text)
    # Store this in persistent context
    context.user_data['note_body'] = note_body
    #logging.info(str(update.message.chat.username) + " adding reminder title: " + rm_title)
    context.bot.send_message(chat_id=update.effective_chat.id, text="Got it, would you like to favorite this note?",
                                    reply_markup=ReplyKeyboardMarkup([["yes", "no"]], resize_keyboard=True, one_time_keyboard=True))
    return NOTES_DONE

def addnotes_fav_done_cb(update: Update, context: CallbackContext) -> int:
    # Get text
    note_favorite = str(update.message.text)
    if note_favorite == "yes":
        context.user_data['note_favorite'] = "1"
    elif note_favorite == "no":
        context.user_data['note_favorite'] = "0"
    else:
        update.message.reply_text(text="Sorry, I didn\'t understand that.")
        context.bot.send_message(chat_id=update.effective_chat.id, text="Got it, would you like to favorite this note?",
                                 reply_markup=ReplyKeyboardMarkup([["yes", "no"]], resize_keyboard=True, one_time_keyboard=True))
        # Loop back
        return NOTES_DONE
    # Fall through
    notes = {"body": context.user_data['note_body'],
             "contact_id":context.user_data['note_contact_id'],
             "is_favorited":context.user_data['note_favorite']}
    MonicaAPI.post_notes(notes)
    update.message.reply_text(text="Done!")
    logging.info(str(update.message.chat.username) + " has POST-ed a note for " + str(context.user_data['note_contact_name']))
    context.user_data.clear()
    return ConversationHandler.END

def addnotes_cancel_cb(update: Update, context: CallbackContext) -> int:
    #Cancels and ends the conversation.
    user = update.message.from_user
    logging.info(str(update.message.chat.username) + " cancelled adding the reminder")
    update.message.reply_text('Oh.. Okay!')
    context.user_data.clear()
    return ConversationHandler.END

GET_NOTES_CONTACT = 1

# /getnotes command callback
# This gets a full list of contacts then asks for the contact ID for the note to be added to
def getnotes_cb(update: Update, context: CallbackContext) -> int:
    # Loggggg
    logging.info(str(update.message.chat.username) + " is getting a note")
    update.message.reply_text(text="Want a note?")
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
    update.message.reply_text(text="Let me know the ID of the contact you want to get a note for!")
    # Proceed to next state and wait for user input
    return GET_NOTES_CONTACT

def getnotes_contact_id_cb(update: Update, context: CallbackContext) -> int:
    # Get contact ID
    note_contact_id = int(update.message.text)
    # Store this in persistent context
    context.user_data['note_contact_id'] = note_contact_id
    # Retrieves contact list from persistent context
    contacts = context.user_data['contacts_dict']
    # Tries to find the name of the contact from the list of dict
    contact_name = next((item for item in contacts if item["id"] == note_contact_id), None)
    
    if contact_name is None:
        update.message.reply_text(text="Oops I can\'t find that contact, please try again!")
        logging.info(str(update.message.chat.username) + " Bruh, invalid ID of " + str(note_contact_id))
        return ConversationHandler.END
    update.message.reply_text(text="I\'ll get notes for " + str(contact_name["name"]))
    logging.info(str(update.message.chat.username) + " is getting a note for " + str(contact_name["name"]))
    notes_dict = MonicaAPI.get_notes(note_contact_id)
    notes_fav = []
    notes_not_fav = []
    for notes in notes_dict:
        if notes['is_favorited'] == True:
            notes_fav.append(notes)
        else:
            notes_not_fav.append(notes)
    notes_fav = sorted(notes_fav, key=lambda d: d['updated_at'], reverse=True)
    notes_not_fav = sorted(notes_not_fav, key=lambda d: d['updated_at'], reverse=True)
    message = ""
    for note in notes_fav:
        if note:
            message = message + "Updated on: " + str(note['updated_at']) + "\n" + str(note['body']) + "\n\n"
    for note in notes_not_fav:
        if note:
            message = message + "Updated on: " + str(note['updated_at']) + "\n" + str(note['body']) + "\n\n"
    if message:
        update.message.reply_text(text=message)
    else:
        update.message.reply_text(text="There is no notes for " + str(contact_name["name"]) + "!")
    context.user_data.clear()
    return ConversationHandler.END

def getnotes_cancel_cb(update: Update, context: CallbackContext) -> int:
    #Cancels and ends the conversation.
    user = update.message.from_user
    logging.info(str(update.message.chat.username) + " cancelled adding the reminder")
    update.message.reply_text('Oh.. Okay!')
    context.user_data.clear()
    return ConversationHandler.END