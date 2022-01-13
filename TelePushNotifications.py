######### System Imports #########
import logging
from datetime import datetime, tzinfo, time
import pytz
from calendar import monthrange
######### Telegram Imports #########
from telegram import Update
from telegram.ext import CallbackContext
######### Custom User Imports #########
import MonicaAPI

# Used to remove jobs in queue if it alr exists
def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        logging.info("Existing job has been removed")
        job.schedule_removal()
    return True

# /notify command callback
def start_notification_cb(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    logging.info(str(update.message.chat.username) + " turned on notifications")
    context.bot.send_message(chat_id=update.effective_chat.id, text='I\'ll be sending you notifications.')

    #context.job_queue.run_repeating(callback_alarm, 2)
    removed = remove_job_if_exists(str(chat_id), context)
    if removed:
        context.bot.send_message(chat_id=update.effective_chat.id, text='You have an existing notification')
    #context.job_queue.run_once(notifications_cb, 1, context=chat_id, name=str(chat_id))
    context.job_queue.run_daily(notifications_cb,
                                # Funky timezone hack
                                # TODO fix this
                                time(hour=(9-8)%24, minute=0),
                                days=(0, 1, 2, 3, 4, 5, 6), context=chat_id, name=str(chat_id))                            


def notifications_cb(context: CallbackContext):
    logging.info("Notification callback is triggered")
    job = context.job
    weekday = datetime.now().weekday()
    today = datetime.now().day
    year = datetime.now().year
    month = datetime.now().month
    num_days = monthrange(year, month)[1]
    # If today is the first day of the month, get reminders for the whole month
    if today == 1:
        month_text = datetime.strptime(str(month), "%m")
        month_text = month_text.strftime("%b")
        print(num_days)
        message = MonicaAPI.get_reminders(num_days)
        if message:
            context.bot.send_message(job.context, text='Reminders for the month of ' + month_text + "!")
            context.bot.send_message(job.context, text=message)
        else:
            context.bot.send_message(job.context, text='You have no reminders for the upcoming week')
    # Else if today is a Sunday, get reminders for upcoming week
    elif weekday == 6:
        message = MonicaAPI.get_reminders(7)
        if message:
            context.bot.send_message(job.context, text='Reminders for the upcoming week!')
            context.bot.send_message(job.context, text=message)
        else:
            context.bot.send_message(job.context, text='You have no reminders for the upcoming week')
    # Else we just get it for the day
    else:
        message = MonicaAPI.get_reminders(1)
        if message:
            context.bot.send_message(job.context, text='Reminders for the day!')
            context.bot.send_message(job.context, text=message)
        else:
            context.bot.send_message(job.context, text='You have no reminders for today')

def stop_notifications_cb(update: Update, context: CallbackContext):
    logging.info(str(update.message.chat.username) + " requested to stop notifications")
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Stopping notifications!' if job_removed else 'You have no active notifications!'
    update.message.reply_text(text)