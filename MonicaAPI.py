import requests
from datetime import datetime, timedelta
from dateutil.rrule import rrule, WEEKLY, MONTHLY, YEARLY

def get_reminders():
    # Get host URL and append "api"
    url_file = open('monica host url.txt', 'r')
    for url in url_file:
        monica_url = url.rstrip('\0')
    url_file.close()
    monica_url = monica_url + "api/"

    # Get authentication token
    token_file = open('monica api token.txt', 'r')
    for token in token_file:
        monica_token = token.rstrip('\0')
    token_file.close()

    # Header for auth
    auth_header = {'Authorization': 'Bearer ' + token}

    # Get contacts
    # Note that for whatever reason the limit is 100 contacts per page
    # Page flipping is uhhh... I don't feel like implementing that
    contacts_url = monica_url + "contacts/?&limit=100"
    #print("GET reqeust to: " + contacts_url)
    r=requests.get(contacts_url, headers=auth_header)
    contact_json = r.json()['data']
    # Date offsets for us to do comparisons on the date
    time_offset = timedelta(weeks=24)
    month_offset = timedelta(weeks=4)
    # Iterate through contacts to gather a full list of reminders
    reminders = str("")
    for contact_index, item in enumerate(contact_json):
        # Print and save contact ID
        # print("\n\nID: " + str(contact_json[contact_index]["id"]))
        contact_id = contact_json[contact_index]["id"]
        # Print full name
        # print("Name: " + contact_json[contact_index]["complete_name"] )
        # Get ALL reminders related to this contact
        contact_reminder_url = monica_url + "contacts/" + str(contact_id) + "/reminders/"
        #print("GET reqeust to: " + contact_reminder_url)
        r=requests.get(contact_reminder_url, headers=auth_header)
        reminder_json = r.json()['data']
        # Iterate through each reminder
        for reminder_index, item in enumerate(reminder_json):
            # Get title
            message = reminder_json[reminder_index]['title']
            # Get frequency type
            reminder_freq = reminder_json[reminder_index]['frequency_type']
            # Get how often to repeat this reminder
            reminder_period = reminder_json[reminder_index]['frequency_number']
            # Get initial date of reminder and convert to datetime format
            reminder_initial_date = reminder_json[reminder_index]['initial_date']
            reminder_initial_date = datetime.strptime(reminder_initial_date, '%Y-%m-%dT%H:%M:%SZ')
            # Now we generate a full list of dates
            # This is list is basically initial date + how often to repeat
            if(reminder_freq == "year"):
                list_dates = list(rrule(YEARLY, dtstart=reminder_initial_date, interval=reminder_period, until=(datetime.now() + time_offset)))
            if(reminder_freq == "month"):
                list_dates = list(rrule(MONTHLY, dtstart=reminder_initial_date, interval=reminder_period, until=(datetime.now() + time_offset)))
            if(reminder_freq == "week"):
                list_dates = list(rrule(WEEKLY, dtstart=reminder_initial_date, interval=reminder_period, until=(datetime.now() + time_offset)))
            else:
                if datetime.now().date() <= reminder_initial_date.date() <= (datetime.now().date() + month_offset):
                    date_print = "(" + str(reminder_initial_date.date()) + ": "
                    name_print = str(contact_json[contact_index]["complete_name"]) + ") "
                    reminders = reminders + date_print + name_print + message + "\n"
            # Now that we have the full list
            # We iterate through this list and compare the reminders that are within the today and the next 4 weeks
            # We treat all events as an all day event
            for reminder_date in list_dates:
                if datetime.now().date() <= reminder_date.date() <= (datetime.now().date() + month_offset):
                    date_print = "(" + str(reminder_date.date()) + ": "
                    name_print = str(contact_json[contact_index]["complete_name"]) + ") "
                    reminders = reminders + date_print + name_print + message + "\n"
    return reminders