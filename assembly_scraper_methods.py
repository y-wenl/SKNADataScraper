#! /usr/bin/python

import logging
logging.basicConfig(level=logging.INFO)

import re
import json

import requests
from bs4 import BeautifulSoup


# Set up base urls

member_list_base = 'http://likms.assembly.go.kr/bill/memVoteResult.do'
member_data_base = 'http://likms.assembly.go.kr/bill/memVoteDetail.do'
member_curdata_base = 'https://www.assembly.go.kr/assm/memPop/memPopup.do'

#bill_list_base = 'http://likms.assembly.go.kr/bill/billVoteResult.do'
bill_votedata_base = 'http://likms.assembly.go.kr/bill/billVoteResultDetail.do'
bill_summdata_base = 'http://likms.assembly.go.kr/bill/billDetail2.do'
bill_list_ajax_base = 'http://likms.assembly.go.kr/bill/billVoteResultListAjax.do'

def scrape_member_list(session: int) -> dict:
    """Given a session (e.g., 21), return a list of Assembly member names and ids.

    Data is returned as a dict, of the form {id:name, id:name, etc}.
    """

    # Get member list page
    logging.info("Downloading member list #" + str(session) + "...")
    website_html = requests.post(member_list_base, data={
        'ageFrom':  session,
        'ageTo':    session,
        'age':      session,
        }).text
    soup = BeautifulSoup(website_html,'lxml')
    logging.info("Done downloading member list")

    # get link for each member
    # Member data links have the form, e.g.:
    # <a href="javascript:fnViewMemDetail('9771145','21')" title="홍준표"> [whitespace and newlines] 홍준표 [whitespace and newlines] </a>
    # or
    # <a href="javascript:fnViewMemDetail('9771046','20')" title="김성태"> [whitespace and newlines] 金成泰  [whitespace and newlines] </a>
    # or
    # <a href="javascript:fnViewMemDetail('9771029','20')" title="최경환"> [whitespace and newlines] 최경환(한)   [whitespace and newlines] </a>
    #
    # Note that each assembly member's name is givin in hangeul under a.title,
    # while their display name may be either hangeul or hanja. Furthermore the
    # display name includes a parenthetical to distinguish lawmakers with
    # identical names.
    #
    # We will just record the display names here. In fact we really just need a
    # list of ids, since we get more complete member data info elsewhere, but
    # the display names will be saved here as well to simplify future debugging.

    member_as = soup.find_all('a', {'href': re.compile('.*:fnViewMemDetail.*')})
    member_names = [a.text.strip() for a in member_as]
    # member_hangeul_names = [a['title'].strip() for a in member_as]
    member_ids = [re.compile("fnViewMemDetail\('([0-9]+)'").search(a.attrs['href']).group(1) for a in member_as]


    # Make sure the name is non-empty
    for member_name in member_names:
        assert(len(member_name) > 0)

    # Ensure each member id is a string of numbers
    for member_id in member_ids:
        assert(re.compile('^[0-9]+$').search(member_id))

    return {x[0]:x[1] for x in zip(member_ids, member_names)}

def scrape_bill_list_data(session):
    # get bill list page
    logging.info("Downloading bill list #" + str(session) + "...")
    bill_list_json = requests.post(bill_list_ajax_base, data={
        'ageFrom': session,
        'ageTo': session,
        'age': session,
        'orderType': 'ASC',
        'strPage': 1,
        'pageSize': '100000',
        #'maxPage': '10',
        'tabMenuType': 'billVoteResult',
        'searchYn': 'ABC',
        }).text
    logging.info("Done downloading bill list")
    bill_list_data = json.loads(bill_list_json)

    return bill_list_data

def scrape_member_data(member_id, session):
    # Get member data page
    logging.info("Downloading member data #" + str(member_id) + "...")

    #website_html = requests.get('{}?dept_cd={}'.format(member_curdata_base, member_id)).text # only for current members of the assembly
    website_html = requests.post(member_data_base, data={
        'ageFrom':  session,
        'ageTo':    session,
        'age':      session,
        'picDeptCd':member_id,
        }).text
    soup = BeautifulSoup(website_html,'lxml')
    logging.info("Done downloading member data")

    # member name
    soup_name_info = soup.find('div', {'class':'personName'})
    member_name = soup_name_info.find('p', {'class':'lang01'}).get_text().strip()
    member_name_alt = None
    if soup_name_info.find('p', {'class':'lang02'}):
        member_name_alt = soup_name_info.find('p', {'class':'lang02'}).get_text().strip()

    # member image url
    member_image_url = None
    soup_image_info = soup.find('div', {'class':'person'}).find('img')
    if soup_image_info:
        member_image_url = soup_image_info.attrs['src']
 

    # member party & district
    soup_pd_info = soup.find('div', {'class': 'personInfo'}).dl
    soup_pd_contents = [x for x in soup_pd_info.contents if type(x) == type(soup_pd_info)] # get bs4 tags from the children (eliminating newlines)
    assert(soup_pd_contents[0].name == 'dt')
    assert(soup_pd_contents[0].text.strip() == '정당')
    assert(soup_pd_contents[1].name == 'dd')
    assert(soup_pd_contents[2].name == 'dt')
    assert(soup_pd_contents[2].text.strip() == '지역구')
    assert(soup_pd_contents[3].name == 'dd')
    member_party = soup_pd_contents[1].text.strip()
    member_district = soup_pd_contents[3].text.strip()


    member_info = {}
    member_info['name'] = member_name
    member_info['name_alt'] = member_name_alt
    member_info['image_url'] = member_image_url
    member_info['party'] = member_party
    member_info['district'] = member_district
    member_info['session'] = session
    member_info['member_id'] = member_id

    return member_info

def scrape_bill_data(bill_no, bill_id, id_master, session):
    # Get bill data page
    logging.info("Downloading bill data #" + bill_id + "...")

    website_html = requests.post(bill_votedata_base, data={
        'age':      session,
        'billNo':   bill_no,
        'billId':   bill_id,
        'idMaster': id_master,
        'tabMenuType': 'billVoteResult',
        }).text
    soup = BeautifulSoup(website_html,'lxml')
    logging.info("Done downloading bill data")

    #import pdb; pdb.set_trace() # DEBUG
    # get summary info

    soup_summary = soup.find('div', {'class':'searchRst'})
    soup_summary_items = soup_summary.find_all('li')
    soup_summary_date_item = [x for x in soup_summary_items if '일자' in x.strong.get_text()][0]
    soup_summary_voters_item = [x for x in soup_summary_items if '표결의원' in x.strong.get_text()][0]
    soup_summary_result_item = [x for x in soup_summary_items if '표결결과' in x.strong.get_text()][0]

    proposal_date = None
    vote_date = None
    date_regex = re.compile('(20[0-9][0-9]-[01]?[0-9]-[0-3]?[0-9])')
    date_searches = [date_regex.search(s.text) for s in soup_summary_date_item.find_all('span')]
    if len(date_searches)==2:
        if date_searches[0]:
            proposal_date = date_searches[0].group(1)
        if date_searches[1]:
            vote_date = date_searches[1].group(1)
    elif len(date_searches)==1:
        if date_searches[0]:
            vote_date = date_searches[0].group(1)

    members_voting = None
    members_registered = None
    voters_regex = re.compile('재석\s*([0-9]+)\s*인.*재적\s*([0-9]+)\s*인')
    voters_search = voters_regex.search(soup_summary_voters_item.span.text)
    if voters_search:
        members_voting = int(voters_search.group(1))
        members_registered = int(voters_search.group(2))

    total_votes = None
    total_agree = None
    total_oppose = None
    total_abstain = None
    result_regex = re.compile('\s*([0-9]+)\s*인\s*\(.*찬성\s*([0-9]+)\s*인.*반대\s*([0-9]+)\s*인.*기권\s*([0-9]+)\s*인')
    result_search = result_regex.search(soup_summary_result_item.span.text)
    assert(result_search)

    total_votes = int(result_search.group(1))
    total_agree = int(result_search.group(2))
    total_oppose = int(result_search.group(3))
    total_abstain = int(result_search.group(4))

    assert(total_agree + total_oppose + total_abstain == total_votes)

    # get voter list info
    soup_box_results = soup.find_all('div', {'class', 'boxResult'})
    assert(len(soup_box_results) == 3)
    soup_box_agree = soup_box_results[0]
    soup_box_oppose = soup_box_results[1]
    soup_box_abstain = soup_box_results[2]
    assert('찬성' in soup_box_agree.p.text)
    assert('반대' in soup_box_oppose.p.text)
    assert('기권' in soup_box_abstain.p.text)

    agree_member_as = soup_box_agree.find('table', {'class', 'status'}).find_all('a')
    oppose_member_as = soup_box_oppose.find('table', {'class', 'status'}).find_all('a')
    abstain_member_as = soup_box_abstain.find('table', {'class', 'status'}).find_all('a')

    id_regex = re.compile("\(['\"]([0-9]+)['\"]\)")
    get_id_from_str = lambda s: id_regex.search(s).group(1) if id_regex.search(s) else None
    a_to_pair = lambda a: {'member_id':get_id_from_str(a.attrs['href']), 'name':a.text.strip()}

    agree_member_list = [a_to_pair(a) for a in agree_member_as]
    oppose_member_list = [a_to_pair(a) for a in oppose_member_as]
    abstain_member_list = [a_to_pair(a) for a in abstain_member_as]

    # import pdb; pdb.set_trace()
    assert(len(agree_member_list) == total_agree)
    assert(len(oppose_member_list) == total_oppose)
    assert(len(abstain_member_list) == total_abstain)

    bill_data = {}
    bill_data['proposal_date'] = proposal_date
    bill_data['vote_date'] = vote_date
    bill_data['members_voting'] = members_voting
    bill_data['members_registered'] = members_registered
    bill_data['total_votes'] = total_votes
    bill_data['total_agree'] = total_agree
    bill_data['total_oppose'] = total_oppose
    bill_data['total_abstain'] = total_abstain
    bill_data['members_agree'] = agree_member_list
    bill_data['members_oppose'] = oppose_member_list
    bill_data['members_abstain'] = abstain_member_list

    return bill_data

