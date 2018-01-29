from datetime import datetime
from utils import next_valid_datetime, ave_or_none, BAD_WORDS_SET
from collections import defaultdict
# from textblob import TextBlob


def build_feature(feature, user_data):
    """
    Parameters:
        feature (:class:`str:`): The name of the feature to build.
        user_data (:class:`dict:`): The dict of the user data information to
            build the feature with.

    Returns:
        The value of the particular feature. Should be a primitive type.
    """
    feature_extractor = FEATURE_EXTRACTORS.get(feature)
    if feature_extractor:
        return feature_extractor(user_data)
    else:
        print "Feature extractor does not exist for: {}".format(feature)


################################################################################
#                            FEATURE EXTRACTORS
################################################################################
def build_num_contacts(user_data):
    """
    Returns :class:`int` number of total contacts.
    """
    num_contacts = 0
    for device_data in user_data.get("devices", []):
        num_contacts += len(device_data.get("contacts", []))
    return num_contacts


def build_num_pound_calls(user_data):
    num_pound_calls = 0
    for device_data in user_data.get("devices", []):
        call_log = device_data.get("call_log", [])
        for call in call_log:
            if "#" in (call.get("phone_number", "") or ""):
                num_pound_calls += 1
    return num_pound_calls


def build_num_pound_sms(user_data):
    num_pound_sms = 0
    for device_data in user_data.get("devices", []):
        for sms in device_data.get("sms_log", []):
            if "#" in (sms.get("sms_address", "") or ""):
                num_pound_sms += 1
    return num_pound_sms


def build_num_star_calls(user_data):
    num_star_calls = 0
    for device_data in user_data.get("devices", []):
        call_log = device_data.get("call_log", [])
        for call in call_log:
            if "*" in (call.get("phone_number", "") or ""):
                num_star_calls += 1
    return num_star_calls


def build_num_star_sms(user_data):
    num_star_sms = 0
    for device_data in user_data.get("devices", []):
        for sms in device_data.get("sms_log", []):
            if "*" in (sms.get("sms_address", "") or ""):
                num_star_sms += 1
    return num_star_sms


def build_ave_duration(user_data):
    total_duration = 0
    num_calls = 0
    for device_data in user_data.get("devices", []):
        call_log = device_data.get("call_log", [])
        num_calls += len(call_log)
        for call in call_log:
            try:
                total_duration += int(call.get("duration", 0))
            except:
                continue
    if num_calls == 0:
        return 0.0
    return ave_or_none(total_duration, num_calls)


def build_call_stats(user_data):
    """
    Find the total and average number of calls, duration, and data_usage.
    """
    total_calls = 0
    total_duration = 0
    # total_data_usage = 0
    # Valid means that these were on days with valid datetimes.
    valid_calls = 0
    valid_duration = 0
    # valid_data_usage = 0
    days_visited = set()
    for device_data in user_data.get("devices", []):
        call_log = device_data.get("call_log", [])
        for call in call_log:
            call_duration = int(call.get("duration", 0) or 0)
            # call_data_usage = int(call.get("data_usage", 0) or 0)
            total_calls += 1
            total_duration += call_duration
            # total_data_usage += call_data_usage
            call_datetime = call.get("datetime")
            if call_datetime and isinstance(call_datetime, datetime):
                days_visited.add(call_datetime.date())
                valid_calls += 1
                valid_duration += call_duration
                # valid_data_usage += call_data_usage

    num_days = len(days_visited)
    return {
        "calls": total_calls,
        "duration(s)": total_duration,
        "ave_daily_calls": ave_or_none(valid_calls, num_days),
        "ave_daily_duration(s)": ave_or_none(valid_duration, num_days)
        # DEPRECATED
        # None of the user data had any data_usage so this is not valuable.
        # "data_usage": total_data_usage,
        # "ave_daily_data_usage": ave_or_none(valid_data_usage, num_days),
    }


def build_ave_daily_sms_count(user_data, require_valid_datetime=True):
    """
    Find the average number of sms per day.

    If `require_valid_datetime` is True, only counts days with a valid datetime,
    otherwise calls without a valid datetime are assumed to be on a day we've
    already counted.
    """
    sms_count = 0
    days_visited = set()
    for device_data in user_data.get("devices", []):
        sms_log = device_data.get("sms_log", [])
        if require_valid_datetime:
            sms_log = filter(
                lambda sms: isinstance(sms.get("datetime"), datetime),
                sms_log
            )
        first = next_valid_datetime(sms_log, key="datetime")
        if first is None:
            # There were no valid datetimes for this device continue
            continue
        if len(sms_log) < 2:
            # Can't compute ave sms without at least 2 smss.
            return None
        last = next_valid_datetime(sms_log, key="datetime", reverse=True)
        for i in range(first, last):
            sms = sms_log[i]
            sms_date = sms.get("datetime")

            # If require_valid_datetime then all smss should be a valid
            # datetime, otherwise try check to be sure.
            if require_valid_datetime or (
                sms_date is not None and isinstance(sms_date, datetime)
            ):
                days_visited.add(sms_date.date())
            else:
                # If this datetime is not valid just assume this call is on a
                # date we've already seen.
                pass
            sms_count += 1
    return ave_or_none(sms_count, len(days_visited))


def build_ave_message_body_length(user_data):
    """
    Find the average message body length over all sms.
    """
    sms_count = 0
    body_length = 0
    for device_data in user_data.get("devices", []):
        sms_log = device_data.get("sms_log", [])
        for sms in sms_log:
            message_body = (sms.get("message_body", "") or "")
            if message_body:
                body_length += len(message_body)
                sms_count += 1
    return ave_or_none(body_length, sms_count)


def build_age_of_contacts_stats(user_data):
    """
    For all contacts with a valid date_added, finds the age of the contact and
    the average age and max age.

    Returns :class:`dict`: A dict with keys, `ave_age` and `max_age` with the
        average and max age of contacts added. Return None if there were no
        contacts or  could not find a valid date_added for any contacts.

    Note: This method does not take into account the possibility of having the
    same contact on different devices.
    """
    age = 0
    num_contacts = 0
    max_age = 0
    now = datetime.now()
    for device_data in user_data.get("devices", []):
        contact_list = device_data.get("contacts", [])
        for contact in contact_list:
            date_added = contact.get("date_added")
            if date_added and isinstance(date_added, datetime):
                try:
                    contact_age = now - date_added
                except TypeError:
                    # If can't subtract offset-naive and offset-aware datetimes
                    # try to convert
                    dt_aware_now = now.replace(tzinfo=date_added.tzinfo)
                    contact_age = dt_aware_now - date_added
                age += contact_age.total_seconds()
                num_contacts += 1
                if age > max_age:
                    max_age = age
    return {
        "ave_age": ave_or_none(age, num_contacts),
        "max_age": max_age or None
    }


def build_interaction_stats(user_data, require_valid_datetime=True):
    """
    Finds all the contacts interacted with and returns the total number of
    contacts interacted with, the average number of contacts interacted with per
    day, and the average number of interactions per day.

    An interaction is defined as sending/receiving a sms or call with a contact.
    """
    contacts_interacted_with = set()
    total_interactions = 0
    total_valid_calls = 0
    total_valid_sms = 0
    contacts_interacted_with_per_day = defaultdict(set)
    for device_data in user_data.get("devices", []):
        sms_log = device_data.get("sms_log", [])
        for sms in sms_log:
            total_interactions += 1
            sms_address = ((sms.get("sms_address", "") or "")).lower()
            if sms_address:
                contacts_interacted_with.add(sms_address)

            sms_datetime = sms.get("datetime")
            if sms_datetime and isinstance(sms_datetime, datetime):
                total_valid_sms += 1
                if sms_address:
                    day = sms_datetime.date()
                    contacts_interacted_with_per_day[day].add(sms_address)

        call_log = device_data.get("call_log", [])
        for call in call_log:
            total_interactions += 1
            phone_number = ((call.get("phone_number", "") or "")).lower()
            if phone_number:
                contacts_interacted_with.add(phone_number)

            call_datetime = call.get("datetime")
            if call_datetime and isinstance(call_datetime, datetime):
                total_valid_calls += 1
                if phone_number:
                    day = call_datetime.date()
                    contacts_interacted_with_per_day[day].add(phone_number)

    num_days = float(len(contacts_interacted_with_per_day))
    total_valid_contacts_interactions = sum([
        len(contacts) for contacts in contacts_interacted_with_per_day.values()
    ])
    return {
        "total_num_contacts_interacted_with": len(contacts_interacted_with),
        "total_interactions": total_interactions,
        "ave_daily_sms": ave_or_none(total_valid_sms, num_days),
        "ave_daily_calls": ave_or_none(total_valid_calls, num_days),
        "ave_daily_contacts_interacted_with": ave_or_none(
            total_valid_contacts_interactions, num_days
        )
    }


def build_sms_message_stats(user_data):
    """
    Returns a set of stats from the actual sms messages including:
     - The total number of bad words used.
     - The ratio of bad to non-bad words used.
     - The total number of messages sent with at least one bad word.

    Note:
     - Sentiment analysis is being done with TextBlob which can currently only
        perform analysis on english text.
     - All bad words are in english. Consider getting a set of bad words in
        other languages.
     - Sentiment analysis has been commented out because TextBlob uses a public
        API to detect language and that makes this script take way too long.



    Things to consider analyzing in this method in the future:
     - non-english messages
     - grammer score
     - spelling score
    """
    num_bad_words_used = 0
    total_words = 0
    derogatory_sms_count = 0
    # sentiment_count = 0
    # polarity = 0
    # subjectivity = 0
    for device_data in user_data.get("devices", []):
        for sms in device_data.get("sms_log", []):
            message_body = (sms.get("message_body", "") or "")
            if len(message_body) > 2:
                # Check if any and count the number of bad words used
                words = message_body.split(" ")
                total_words += len(words)
                bad_words_used = set(words) & BAD_WORDS_SET
                num_bad_words = len(bad_words_used)
                num_bad_words_used += num_bad_words
                if num_bad_words > 0:
                    derogatory_sms_count += 1

                # TODO: Find something better/faster than TextBlob for sentiment
                # analysis. Build you're own model using NLTK.
                # # TextBlob sentiment analysis
                # message_blob = TextBlob(message_body)
                # if message_blob.detect_language() == "en":
                #     sentiment_count += 1
                #     message_blob.sentiment.polarity
                #     message_blob.sentiment.subjectivity

    return {
        "num_bad_words_used": num_bad_words_used,
        "ratio_of_bad_words_used": ave_or_none(num_bad_words_used, total_words),
        "num_derogatory_sms": derogatory_sms_count,
        # "sentiment_polarity": ave_or_none(polarity, sentiment_count),
        # "sentiment_subjectivity": ave_or_none(subjectivity, sentiment_count)
    }

FEATURE_EXTRACTORS = {
    "num_contacts": build_num_contacts,
    # "num_calls_to_international": build_num_calls_to_international,
    # "num_calls_from_international": build_num_calls_from_international,
    "num_#_calls": build_num_pound_calls,
    "num_#_sms": build_num_pound_sms,
    "num_*_calls": build_num_star_calls,
    "num_*_sms": build_num_star_sms,
    "ave_duration(s)": build_ave_duration,
    "call_stats": build_call_stats,
    "ave_daily_sms_count": build_ave_daily_sms_count,
    "ave_message_body_length": build_ave_message_body_length,
    "interaction_stats": build_interaction_stats,
    "sms_message_stats": build_sms_message_stats,
    # DEPRECATED until we can get reliable `date_added` information.
    # "age_of_contacts_stats": build_age_of_contacts_stats,
    # "ave_num_times_contacted": build_ave_num_times_contacted,  # I don't know
    #   how to tell when someone was contacted, vs contacting.
    # Find which words or phrases are most relevant to repaid/defaulted (build
    #   word association)
    # # "Sylviah, don't let a small debt affect your credit history. You are 16
    #   days late on your Branch loan! Honour your debt of Ksh 852 to Paybill:
    #   998608."
    # # What is call_type?
    # # Connected graph
    # # how many contacts do you have of people who defaulted / repaid. Can't do
    #   this because I don't have the phone numbers of the users. But I imagine
    #   this would be interesting to check.
    # Number of contacts in common with people who defauled / repaid
    # Number of people interacted with in common with people who defaulted /
    #   repaid
}

ALL_FEATURES = FEATURE_EXTRACTORS.keys()
