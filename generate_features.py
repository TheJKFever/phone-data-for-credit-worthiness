# -*- coding: utf-8 -*-
"""
Python 2.7

This script reads in a set of user data, calculates feature data from it, and
then saves that feature data back to a file to be used for data modeling.

The folder structure of DATA_PATH looks like the following.
|- user_logs
    |- user-{user_id}
         |- device-1 # There will always be at least one device.
         |   |- collated_call_log.txt
         |   |- collated_contact_list.txt
         |   |- collated_sms_log.txt
         |-device-2 # Potentially 2 or more other devices.

The desired output is a file of features for each user like so (Note the real
file will be in csv format):
user_id |   status   | feature_1_name | feature_2_name | ... | feature_n_name
   1    | defaulted  |            100 |            .75 | ... |              3
   ...
   350  |   repaid   |            421 |            .97 | ... |             11
"""
from os import listdir
from os.path import isfile
from datetime import datetime
import dateutil.parser
import csv
import json
from features import ALL_FEATURES, build_feature
progress_installed = False
try:
    from progress.bar import Bar
    progress_installed = True
except:
    print (
        "To see pretty status bars while this script is loading please install "
        "`progress` with `pip install progress`"
    )


CALL_LOG_FILENAME = "collated_call_log.txt"
CONTACT_LIST_FILENAME = "collated_contact_list.txt"
DATA_PATH = "./user_logs/"
SMS_LOG_FILENAME = "collated_sms_log.txt"
USER_STATUS_FILE = "user_status.csv"
DEVICE_DATA_FILES = set([
    CALL_LOG_FILENAME,
    CONTACT_LIST_FILENAME,
    SMS_LOG_FILENAME
])


def build_user_folder_path(user_id):
    return DATA_PATH + "user-{}".format(user_id)


def read_json_file(file_path, default=None):
    if not isfile(file_path):
        # print("{} does not exist.".format(file_path))
        return default
    try:
        file = open(file_path, "r")
        txt_data = file.read()
        json_data = json.loads(txt_data)
        return json_data
    except IOError:
        print("Could not json parse {}. returning: {}".format(
            file_path,
            default
        ))
        return default


def parse_timestamp(timestamp_txt, default=None):
    try:
        try:
            timestamp = int(timestamp_txt) / 1000
            if timestamp == 0:
                return default
        except ValueError:
            # Try parsing iso format
            return dateutil.parser.parse(timestamp_txt)
        else:
            return datetime.fromtimestamp(timestamp)
    except:
        # Invalid datetime, return default.
        print("Received an invalid timestamp: {}".format(timestamp_txt))
        return default


def build_contact_list(device_folder_path):
    contact_list_path = "/".join([device_folder_path, CONTACT_LIST_FILENAME])
    contact_list = read_json_file(contact_list_path, default=[])
    for contact in contact_list:
        for date_fild in ["date_added", "last_time_contacted"]:
            if date_fild in contact:
                contact[date_fild] = parse_timestamp(contact[date_fild])
    return contact_list


def build_call_log(device_folder_path):
    call_log_path = "/".join([device_folder_path, CALL_LOG_FILENAME])
    call_log = read_json_file(call_log_path, default=[])
    for call in call_log:
        if "datetime" in call:
            call["datetime"] = parse_timestamp(call["datetime"])
    return call_log


def build_sms_log(device_folder_path):
    sms_log_path = "/".join([device_folder_path, SMS_LOG_FILENAME])
    sms_log = read_json_file(sms_log_path, default=[])
    for sms in sms_log:
        if "datetime" in sms:
            sms["datetime"] = parse_timestamp(sms["datetime"])
    return sms_log


def build_user_device_data(user_id):
    device_data = []
    user_folder_path = build_user_folder_path(user_id)
    for device_folder in listdir(user_folder_path):
        device_folder_path = "/".join([user_folder_path, device_folder])
        # The lines below are commented out because every device_folder_path
        # was a folder with at least one data file. But this may be useful for
        # larger parsings.
        # # Make sure this is a folder with at least one of the desired files:
        # try:
        #     assert isdir(device_folder_path)
        #     assert len(DEVICE_DATA_FILES & set(listdir(device_folder_path)))
        # except:
        #     print("{} contained no user data files.".format(device_folder_path))
        #     continue
        # else:
        device_data.append({
            "call_log": build_call_log(device_folder_path),
            "contacts": build_contact_list(device_folder_path),
            "sms_log": build_sms_log(device_folder_path)
        })
    return device_data


def build_users():
    """
    Builds the core user data structure from the provided user data.
    Returns:
        :class:`dict` A structure mapping a user ID to the associated data.

    {
        1: {
            "status": defaulted,
            "devices": [{
                "contacts": [...],  # A list of all the users contacts
                "sms_log": [...],  # A list of all the users sms's
                "call_log": [...]  # A list of call history
            }]
        },
        ...
    }
    """
    users = {}
    with open(DATA_PATH + USER_STATUS_FILE, "r") as csvfile:
        user_status_data = list(csv.DictReader(csvfile))
        num_users = len(user_status_data)
        if progress_installed:
            bar = Bar("Reading user file", max=num_users)
        for row in user_status_data:
            user_id = row.get("user_id")
            user = {
                "status": row.get("status"),
                "devices": build_user_device_data(user_id)
            }
            users[user_id] = user
            if progress_installed:
                bar.next()
        if progress_installed:
            bar.finish()
    return users


users_features = {}
users = build_users()
num_users = len(users)
if progress_installed:
    bar = Bar("Generating features", max=num_users)
possible_features = set(["user_id", "status"])
for user_id, user_data in users.items():
    user_features = {
        "user_id": user_id,
        "status": user_data.get("status")
    }
    for feature in ALL_FEATURES:
        feature_data = build_feature(feature, user_data)
        # Some features return dicts with multiple data points.
        if isinstance(feature_data, dict):
            user_features.update(feature_data)
            possible_features |= set(feature_data.keys())
        else:
            user_features[feature] = build_feature(feature, user_data)
            possible_features.add(feature)

    users_features[user_id] = user_features
    if progress_installed:
        bar.next()
if progress_installed:
    bar.finish()

with open("feature_data.csv", "w") as csvfile:
    fieldnames = possible_features
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(users_features.values())
