# Generate feature data from users phone information.

A script to generate feature data from users phone information and the
functions for generating each feature.

To see pretty status bars while this script is running install progress with:
```
pip install progress
```

To run:
First make sure that the user data is stored at `user_logs/` or else change `DATA_PATH` in `generate_features.py`.
```
python generate_features.py
```

This will create a file called `feature_data.csv`.


## Notes I took while developing this script to track my thought process:

I wanted to come up with a list of possible features that I would want to collect that would be relevant to credit worthiness. So I first asked, what are key metrics that credit agencies currently use to measure my credit worthiness. Based off CreditKarma and CreditSesame here are some things that determine my credit score:
 - How much credit I'm using of what's available
 - Payment history
 - Derogatory Marks
 - Credit Age
 - Total number of accounts
 - Number of Hard Inquiries


**Notes while reading and parsing data:**

I attempted to read in all the user data and while reading it in found these errors:
Could not json parse ./user_logs/user-55/device-1/collated_sms_log.txt.
./user_logs/user-83/device-1 contained no user data files.
./user_logs/user-110/device-2 contained no user data files.
Could not json parse ./user_logs/user-184/device-3/collated_sms_log.txt.

In deed user 83 and 110 had an empty device folder and user 55 and 184 were missing an sms log file.
I deleted the empty device folders and silenced the other errors.

I wanted to see all the possible keys from the contacts list, sms_log, and call_log to help determine what features are possible to extract. I used this to collect it:
```
contact_keys = set([])
sms_keys = set([])
call_keys = set([])
for user_data in users.values():
    for device_data in user_data.get("devices", []):
        for contact in device_data.get("contacts", []):
            contact_keys |= set(contact.keys())
        for sms in device_data.get("sms_log", []):
            sms_keys |= set(sms.keys())
        for call in device_data.get("call_log", []):
            call_keys |= set(call.keys())
```

This was the output
```
In [5]: contact_keys
Out[5]:
{u'date_added',
 u'display_name',
 u'item_id',
 u'last_time_contacted',
 u'phone_numbers',
 u'photo_id',
 u'times_contacted'}

# get all keys for sms's
In [6]: sms_keys
Out[6]:
{u'contact_id',  # Seems irrelevant
 u'datetime',
 u'item_id',
 u'message_body',
 u'sms_address',
 u'sms_type',
 u'thread_id'}

# get all keys for calls
In [7]: call_keys
Out[7]:
{u'cached_name',
 u'call_type',
 u'country_iso',
 u'data_usage',
 u'datetime',
 u'duration',
 u'features_video',
 u'geocoded_location',
 u'is_read',
 u'item_id',
 u'phone_number'}
```

**Here's a list of all the features I thought of just from looking at the possible data points:**

 - number of total contacts
 - number of international calls
 - number of calls from international numbers
 - number of # calls / sms
 - number of * calls / sms
 - average duration of call
 - average monthly usage of minutes
 - average number of monthly calls / sms
 - average message body length
 - average length of known contacts
 - longest length of known contact
 - number of contacts contacted within a week
 - percent of contacts contacted withing a week
 - average number of times contacted
 - overall sms sentiment positive/negative
 - number of bad words used in sms
 - number of derogatory smss
 - grammer score
 - spelling score
 - Find which words or phrases are most relevant to repaid/defaulted (build word count)
Here's an example of an sms that might be relevant: "Sylviah, don't let a small debt affect your credit history. You are 16 days late on your Branch loan! Honour your debt of Ksh 852 to Paybill: 998608."
 - total data_usage
Connected graph: how many contacts do you have of people who defaulted / repaid. Can't do this because I don't have the phone numbers of the users. But I imagine this would be interesting to check.
 - Number of contacts in common with people who defauled / repaid
 - Number of people interacted with in common with people who defaulted / repaid

Questions I have:
 - What is call_type?


I turned all datetimes into python datetimes objects to make comparisons easier:

contact_list:
 - date_added
 - last_time_contacted

sms_log:
 - datetime

call_log:
 - datetime


After writing all the features and outputting the data to a csv file, I inspected the data.
Looking at the data I saw this:
```
ave_daily_interactions |  ave_daily_sms_count
36.1945945945946       |  77.07462686567165
```

I know that an sms is an interaction so the number of daily interactions should never be below the number of daily sms. But then I realized, the ave_daily_sms_count is counting the average number of sms sent/received on any day that an sms was sent or received. It's not going day by day and asking how many were sent on that day. So what this means is that there may have been days with tons of sms sent/received, but days with none sent. And on those days with no sms sent/received, if there was one phone call, that would drastically change the ave_daily_interactions. Because of this, I decided to move the ave_daily_sms_count into the build_interaction_stats method and average over all days with interactions which should normalize ave_daily_sms_count and ave_daily_call_count.

It turns out that only one of the contacts actually has valid "date_added" information, so I decided to remove the `age` and `max_age` fields, since we wouldn't be able to do much with it.
