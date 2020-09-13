#! /usr/bin/python

import os
import re
import datetime
import time
import json
from vote_scraper_methods import *
from copy import copy,deepcopy

all_sessions = [20, 21]
current_session = 21

data_dir = 'data'

########## Update bill lists ##########

# * Don't update past sessions if we have the data
# * Update current session if data age > 1 week
bill_list_freshness_age_limit = 7 * 24 * 3600 # freshness limit in seconds

bill_list_data_filename_regex = re.compile('bill_list_data_session([2-9][0-9])_dltime([0-9]+).json')
bill_list_data_filename_template = 'bill_list_data_session{}_dltime{}.json'

# Figure out which sessions need to be downloaded
bill_sessions_to_dl = set(all_sessions)
for filename in os.listdir(data_dir):
    filepath = os.path.join(data_dir, filename)

    bill_list_data_filename_search = bill_list_data_filename_regex.search(filename)
    if bill_list_data_filename_search:
        session = int(bill_list_data_filename_search.group(1))

        if session == current_session:
            dltime = int(bill_list_data_filename_search.group(2))

            curtime = time.time()
            age_secs_filename = curtime - dltime

            if age_secs_filename < bill_list_freshness_age_limit:
                # if bill data is sufficiently fresh, no need to download it again
                bill_sessions_to_dl -= set([session])
        else:
            # if bill data exists for a prior session, no need to download it again
            bill_sessions_to_dl -= set([session])


# Download and save relevant sessions
curtime = int(time.time())
for session in bill_sessions_to_dl:
    bill_list_data = scrape_bill_list_data(session)
    json_data = json.dumps(bill_list_data, ensure_ascii=False)
    output_filename = bill_list_data_filename_template.format(session, curtime)
    output_filepath = os.path.join(data_dir, output_filename)
    with open(output_filepath, 'w') as f:
        f.write(json_data)
        print("Saved to {}.".format(output_filepath))


# Load bill_list_data
bill_list_filepaths = {}
freshest_bill_list_times = {s:0 for s in all_sessions}
for filename in os.listdir(data_dir):
    filepath = os.path.join(data_dir, filename)

    bill_list_data_filename_search = bill_list_data_filename_regex.search(filename)
    if bill_list_data_filename_search:
        session = int(bill_list_data_filename_search.group(1))
        dltime = int(bill_list_data_filename_search.group(2))
        if dltime > freshest_bill_list_times[session]:
            bill_list_filepaths[session] = filepath
            freshest_bill_list_times[session] = dltime

bill_list_datas = {}
for session in all_sessions:
    with open(bill_list_filepaths[session], 'r') as f:
        bill_list_datas[session] = json.load(f)


#######################################

########## Update bill data ##########

bill_data_filename_regex = re.compile('bill_data_session([2-9][0-9])_no([^_]*)_id(.*).json')
bill_data_filename_template = 'bill_list_data_session{}_no{}_id{}.json'

##### Download bill vote data
bill_data_dir = os.path.join(data_dir, 'bills')
for session in [21]:#all_sessions:
    bill_list_data = bill_list_datas[session]
    bill_list = bill_list_data['resListVo']
    for bill in bill_list:
        bill_no = bill['billno']
        bill_id = bill['billid']
        bill_id_master = bill['idmaster']

        bill_filename = bill_data_filename_template.format(session, bill_no, bill_id)
        bill_filepath = os.path.join(bill_data_dir, bill_filename)
        if not os.path.isfile(bill_filepath):
            # scrape data and save
            try:
            #if True:
                bill_data = scrape_bill_data(bill_no, bill_id, bill_id_master, session)
                bill_data['result'] = bill['result']
                bill_data['name'] = bill['billname']
                bill_data['kind'] = bill['billkindcd']
                bill_data['committee'] = bill['currcommitte'] if 'currcommitte' in bill else None
                with open(bill_filepath, 'w') as f:
                    json.dump(bill_data, f, ensure_ascii=False)
            except:
                donothing = True # probably some download error...

######################################

########## Update member data ##########
member_list_freshness_age_limit = 30 * 24 * 3600 # freshness limit in seconds

member_list_data_filename_regex = re.compile('member_list_data_session([2-9][0-9])_dltime([0-9]+).json')
member_list_data_filename_template = 'member_list_data_session{}_dltime{}.json'

member_info_data_filename_regex = re.compile('member_info_data_session([2-9][0-9]).json')
member_info_data_filename_template = 'member_info_data_session{}.json'

# Figure out which sessions need to be downloaded
member_sessions_to_dl = set(all_sessions)
for filename in os.listdir(data_dir):
    filepath = os.path.join(data_dir, filename)

    member_list_data_filename_search = member_list_data_filename_regex.search(filename)
    if member_list_data_filename_search:
        session = int(member_list_data_filename_search.group(1))

        if session == current_session:
            dltime = int(member_list_data_filename_search.group(2))

            curtime = time.time()
            age_secs_filename = curtime - dltime

            if age_secs_filename < member_list_freshness_age_limit:
                # if member data is sufficiently fresh, no need to download it again
                member_sessions_to_dl -= set([session])
        else:
            # if member data exists for a prior session, no need to download it again
            member_sessions_to_dl -= set([session])

# Download and save relevant sessions
curtime = int(time.time())
for session in member_sessions_to_dl:
    member_list_data = scrape_member_list(session)
    json_data = json.dumps(member_list_data, ensure_ascii=False)
    output_filename = member_list_data_filename_template.format(session, curtime)
    output_filepath = os.path.join(data_dir, output_filename)
    with open(output_filepath, 'w') as f:
        f.write(json_data)
        print("Saved to {}.".format(output_filepath))

# Load member_list_data
member_list_filepaths = {}
freshest_member_list_times = {s:0 for s in all_sessions}
for filename in os.listdir(data_dir):
    filepath = os.path.join(data_dir, filename)

    member_list_data_filename_search = member_list_data_filename_regex.search(filename)
    if member_list_data_filename_search:
        session = int(member_list_data_filename_search.group(1))
        dltime = int(member_list_data_filename_search.group(2))
        if dltime > freshest_member_list_times[session]:
            member_list_filepaths[session] = filepath
            freshest_member_list_times[session] = dltime

member_list_datas = {}
for session in all_sessions:
    with open(member_list_filepaths[session], 'r') as f:
        member_list_datas[session] = json.load(f)

##### Read all the past bills to get the ids of any members missing from the member lists

all_member_ids = {s:set(member_list_datas[s]) for s in all_sessions}
for session in all_sessions:
    for filename in [x for x in os.listdir(bill_data_dir) if 'session{}_'.format(session) in x]:
        filepath = os.path.join(bill_data_dir, filename)
        with open(filepath, 'r') as f:
            this_data = json.load(f)
        this_member_ids = [x['member_id'] for x in (this_data['members_agree'] + this_data['members_oppose'] + this_data['members_abstain'])]
        all_member_ids[session].update(set(this_member_ids))

##### Download any missing member info

# load member info files and download any missing data
maxdl = 10000
for session in all_sessions:
    curdl = 0
    filename = member_info_data_filename_template.format(session)
    filepath = os.path.join(data_dir, filename)

    # create member info files if they don't exist
    if not os.path.isfile(filepath):
        with open(filepath, 'w') as f:
            json.dump({}, f)

    with open(filepath, 'r') as f:
        member_info_data = json.load(f)

    existent_member_info_ids = list(member_info_data.keys())
    
    for member_id in all_member_ids[session]:
        if curdl >= maxdl:
            break
        if not (member_id in member_info_data):
            try:
                member_info_datum = scrape_member_data(member_id, session)
                member_info_data[member_id] = member_info_datum
                curdl += 1
            except:
                donothing = True # probably some download error.....

    new_member_info_ids = list(member_info_data.keys())

    if len(new_member_info_ids) > len(existent_member_info_ids):
        print("Saving new member data to {}.".format(filepath))
        with open(filepath, 'w') as f:
            json.dump(member_info_data, f, ensure_ascii=False, indent=1)

########################################
