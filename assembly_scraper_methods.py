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




def scrape_bill_list_data(session:int) -> dict:
    """Given a session (e.g., 21), return a list of bills voted on.

    Data is returned as a dict, directly from the ajax request.
    This dict has the form:
    'ageMap': {
        'ord': session number as int (e.g. 21),,
        'age': session number as str (e.g. '21'),,
        'ageName': session name in Korean (e.g. '제21대'),
        'startDt': YYYYMMDD,
        'endDt': YYYYMMDD,
        'sessionFrom': ? (e.g. 379),
        'sessionTo': ? (e.g. 388)
        }
    'ageList': [ageMap]
    'allCount': Total number of bills
    'billKindList': List of dicts, each for a bill type (e.g. 헌법개정)
    'paramMap': Dict containing bill search request data
                Not really important I think.
    'countVec': List of dicts, each telling the number of bills for a given
                committee.
    'resListVo': List of dicts, each dict describing a bill. The dict for each
                 bill has the form
                {
                'billid': Bill ID string (e.g. 'PRC_A2H1K0K4I1G4X1Z7Q4W4S4N7E1W1F7'),
                'billno': Bill number, as a string (e.g. '2110283'),
                'billkindcd': Bill type (e.g. '법률안'),
                'age': session number as str (e.g. '21'),
                'billname': Bill name string
                'processdate': YYYY-MM-DD,
                'idmaster': int, idk what this is (e.g. 195858),
                'sessioncd': ? (e.g. 387),
                'currentscd': ? (e.g. 2),
                'currcommitte': committee string (e.g. '보건복지위원회'),
                'mtcnt': # of assembly members (I think?) (e.g. 300),
                'vtcnt': # of members voting on the bill (e.g. 203),
                'agree': # of members voting yes (e.g. 202),
                'withdraw': # of members abstaining (e.g. 1),
                'disagree': # of members voting no (e.g. 0),
                'xx': ? (e.g. 97),
                'result': string indicating passage or not (e.g.'원안가결')
                }
    """

    # get bill list data
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

    # remove seq and page keys, since these change regularly and take up space in git
    for b in bill_list_data['resListVo']:
        del(b['seq'])
        del(b['page'])

    # no processing, just return the result as-is
    return bill_list_data

def scrape_member_data(member_id:str, session:int) -> dict:
    """Given a member id (e.g., "9771165") and session (e.g., 21), return data
    of the relevant Assembly member.

    Data is returned as a dict, of the form
        {
            'name':      member name (str)
            'name_alt':  alternative member name (e.g. hanja or hangeul version)
                         str or None
            'image_url': url of member mugshot
                         str or None
            'party':     member party (str)
            'district':  member district represented (str)
                         For party-list members, this is 비례대표
            'session':   session number
            'member_id': member id (str)
        }
    """

    # Get member data pages
    logging.info("Downloading member data #" + str(member_id) + "...")

    #website_html = requests.get('{}?dept_cd={}'.format(member_curdata_base, member_id)).text # only for current members of the assembly

    website_html = requests.post(member_data_base, data={
        'ageFrom':  session,
        'ageTo':    session,
        'age':      session,
        'picDeptCd':member_id,
        }).text
    soup = BeautifulSoup(website_html,'lxml')

    website_html2 = requests.post(member_curdata_base, data={
        'dept_cd':member_id,
        }).text
    soup2 = BeautifulSoup(website_html2,'lxml')

    logging.info("Done downloading member data")

    ## scrape basic data page

    # member name
    soup_name_info = soup.find('div', {'class':'personName'})
    member_name = soup_name_info.find('p', {'class':'lang01'}).get_text().strip()
    assert(len(member_name) > 0)
    member_name_alt = None
    if soup_name_info.find('p', {'class':'lang02'}):
        member_name_alt = soup_name_info.find('p', {'class':'lang02'}).get_text().strip()

    # member image url
    member_image_url = None
    soup_image_info = soup.find('div', {'class':'person'}).find('img')
    if soup_image_info:
        member_image_url = soup_image_info.attrs['src']

        # Only save image url if it matches something sane.
        # No need to abort if it doesn't; we don't care about missing pictures.
        if not re.compile("^https?://([a-zA-Z0-9]*\.)assembly\.go\.kr/.*", re.I).search(member_image_url):
            member_image_url = None
 

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
    assert(len(member_party) > 0)
    assert(len(member_district) > 0)

    ## scrape in-depth data page
    soup_box_info = soup2.find("div", {"class":"info_mna"})
    soup2_name = soup_box_info.find("h4").get_text().strip()
    assert(soup2_name in [member_name, member_name_alt])
    # should be '', alt_name, romanized name, and date of birth
    profile_items = [x.get_text().strip() for x in soup_box_info.find("div", {"class":"profile"}).find_all("li")]
    soup_pro_info = soup_box_info.find("dl", {"class":"pro_detail"})
    pro_dict = {}
    soup_pro_next_dt = soup_pro_info.find("dt")
    soup_pro_next_dd = soup_pro_next_dt.find_next_sibling("dd")
    while (soup_pro_next_dt and soup_pro_next_dd):
        pro_dict[soup_pro_next_dt.get_text().strip()] = soup_pro_next_dd.get_text().strip()
        soup_pro_next_dt = soup_pro_next_dd.find_next_sibling("dt")
        if soup_pro_next_dt is not None:
            soup_pro_next_dd = soup_pro_next_dt.find_next_sibling("dd")

    # get member romanized name
    member_roman_name = None
    for profile_item in profile_items:
        if len(profile_item) > 0:
            this_roman_match = re.match("[a-zA-Z][a-zA-Z -.]*", profile_item)
            if this_roman_match:
                member_roman_name = this_roman_match.group(0).upper()

    # get member date of birth
    member_dob = None
    for profile_item in profile_items:
        if len(profile_item) > 0:
            this_dob_match = re.match("[12][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]", profile_item)
            if this_dob_match:
                member_dob = this_dob_match.group(0)

    # get committees
    member_committees = []
    if "소속위원회" in pro_dict:
        member_committees = [x.strip() for x in pro_dict["소속위원회"].split(",")]

    # get terms in office
    member_terms = None
    if "당선횟수" in pro_dict:
        terms_match = re.match("^\s*(\w[0-9]*)선", pro_dict["당선횟수"])
        if terms_match:
            if terms_match.group(1) == "초":
                member_terms = 1
            elif terms_match.group(1) == "재":
                member_terms = 2
            else:
                try:
                    member_terms = int(terms_match.group(1))
                except ValueError:
                    member_terms = None

    # get phone number etc
    member_phone = pro_dict.get("사무실 전화", None)
    member_office = pro_dict.get("사무실 호실", None)
    member_website = pro_dict.get("홈페이지", None)
    member_email = pro_dict.get("이메일", None)


    member_info = {}
    member_info['name']         = member_name
    member_info['name_alt']     = member_name_alt
    member_info['image_url']    = member_image_url
    member_info['party']        = member_party
    member_info['district']     = member_district
    member_info['session']      = session
    member_info['member_id']    = member_id

    member_info['roman_name']   = member_roman_name
    member_info['dob']          = member_dob
    member_info['committees']   = member_committees
    member_info['terms']        = member_terms
    member_info['phone']        = member_phone
    member_info['office']       = member_office
    member_info['website']      = member_website
    member_info['email']        = member_email

    return member_info

def scrape_bill_data(bill_no:str, bill_id:str, id_master:int, session:int) -> dict:
    """Given a bill no (e.g., "2110283"),
       id (e.g. "PRC_A2H1K0K4I1G4X1Z7Q4W4S4N7E1W1F7"), and
       id_master (e.g., 195858),
       return voting result and summary data of the relevant bill.

       Data is returned as a dict, of the form
       {

            bill_id:         bill_id
            bill_no:         bill_no
            id_master:       id_master
            session:         session

            name:            bill name (str)
            summary:         bill summary (str or None)
            related_bill_ids: list of bill_ids of related bills

            proposal_date:   YYYY-MM-DD
            vote_date:       YYYY-MM-DD

            total_members:   total # of members in the assembly
            total_votes:     total # voting on this motion
            total_agree:     total # voting agree
            total_oppose:    total # voting oppose
            total_abstain:   total # voting abstain
                             This is the number abstaining _while present_
                             NOT the number who just don't show up

            members_agree:   List of members voting agree
            members_oppose:  List of members voting oppose
            members_abstain: List of members voting abstain
       }
    """

    # We need to get data fom 2 pages: the bill vote data page, and the bill
    # summary data page.

    # Get bill vote data page
    logging.info("Downloading bill vote data #" + bill_id + "...")

    website_html = requests.post(bill_votedata_base, data={
        'age':      session,
        'billNo':   bill_no,
        'billId':   bill_id,
        'idMaster': id_master,
        'tabMenuType': 'billVoteResult',
        }).text
    soup = BeautifulSoup(website_html,'lxml')
    logging.info("Done downloading bill vote data")

    soup_mainsec = soup.find('div', {'class':'searchRst'})
    soup_mainsec_items = soup_mainsec.find_all('li')
    soup_mainsec_date_item = [x for x in soup_mainsec_items if '일자' in x.strong.get_text()][0]
    soup_mainsec_voters_item = [x for x in soup_mainsec_items if '표결의원' in x.strong.get_text()][0]
    soup_mainsec_result_item = [x for x in soup_mainsec_items if '표결결과' in x.strong.get_text()][0]

    proposal_date = None
    vote_date = None
    date_regex = re.compile('(20[0-9][0-9]-[01]?[0-9]-[0-3]?[0-9])')
    date_searches = [date_regex.search(s.text) for s in soup_mainsec_date_item.find_all('span')]
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
    voters_search = voters_regex.search(soup_mainsec_voters_item.span.text)
    if voters_search:
        members_voting = int(voters_search.group(1))
        members_registered = int(voters_search.group(2))

    total_votes = None
    total_agree = None
    total_oppose = None
    total_abstain = None
    result_regex = re.compile('\s*([0-9]+)\s*인\s*\(.*찬성\s*([0-9]+)\s*인.*반대\s*([0-9]+)\s*인.*기권\s*([0-9]+)\s*인')
    result_search = result_regex.search(soup_mainsec_result_item.span.text)
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

    assert(len(agree_member_list) == total_agree)
    assert(len(oppose_member_list) == total_oppose)
    assert(len(abstain_member_list) == total_abstain)


    # Get bill summary data page
    logging.info("Downloading bill summary data #" + bill_id + "...")
    summ_website_html = requests.post(bill_summdata_base, data={
        'billId':   bill_id,
        }).text
    summ_soup = BeautifulSoup(summ_website_html,'lxml').find('div', {'class': 'subContents'})
    logging.info("Done downloading bill summary data")

    # get bill name
    summ_soup_name_item = summ_soup.find('h3', {'class':'titCont'})

    name_regex = re.compile("^\s*\[" + str(bill_no) + "\]\s*(.*)\s*$")
    assert(name_regex.search(summ_soup_name_item.text))
    bill_name = name_regex.search(summ_soup_name_item.text).group(1).strip()
    assert(len(bill_name) > 0)

    # get bill summary
    # note that not all bills have summaries available
    bill_summary = None
    if summ_soup.find('div', {'id':'summaryContentDiv'}):
        bill_summary = summ_soup.find('div', {'id':'summaryContentDiv'}).text.strip()
        if len(bill_summary) == 0:
            bill_summary = None

    # get related bills
    other_bill_url_rex = re.compile('/bill/billDetail.do\?billId=([a-zA-Z0-9_-]*)')
    summ_soup_other_bill_items = summ_soup.find_all('a', {'href': other_bill_url_rex})
    related_bill_ids = [other_bill_url_rex.search(a['href']).group(1) for a in summ_soup_other_bill_items]

    # eliminate duplicates and the current bill from related_bill_ids
    related_bill_ids = list(set(related_bill_ids) - set([bill_id]))

    # put data into dict

    bill_data = {}

    bill_data['bill_id'] = bill_id
    bill_data['bill_no'] = bill_no
    bill_data['id_master'] = id_master
    bill_data['session'] = session

    bill_data['name'] = bill_name
    bill_data['summary'] = bill_summary
    bill_data['related_bill_ids'] = related_bill_ids

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

