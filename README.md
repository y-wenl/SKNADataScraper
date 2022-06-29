# South Korean National Assembly legislative data scraper

## Overview
This code scrapes the [National Assembly website](https://likms.assembly.go.kr/bill/main.do), and is used to power [politopic.net](https://politopic.net).

It produces the following output:
1. The current members of the National Assembly and their information.
    - `member_list_data_session21.json`, a simple list of member names and corresponding ID numbers.
    - `member_info_data_session21.json`, a list containing detailed information on each member.
2. A list of all bills voted on in the specified session (currently session 21, for 2020-2024).
    - `bill_list_data_session21.json`, raw output from the National Assembly website AJAX request. The key variable is `resListVo`, which contains a list of every bill, including the bill name and ID numbers.
3. Detailed information on each bill in the list.
    - `bills/` directory containing a JSON file for each bill. Each JSON file includes not only the bill name and ID numbers, but also the relevant committee and a list of ever assembly member's vote on the bill.

## Usage

- Install python 3 and the packages in `requirements.txt` (requests, beautifulsoup4, lxml, jsbeautifier).

- Run `scrape_vote_data.py`. Output data will be saved to `../data` (there is currently no configuration option, but you can change the `data_dir` variable near the top of `scrape_vote_data.py`. Note that there are thousands of bills, so it will take some time. If the process is interrupted, just run it again; it will not re-download bills it has already saved.

- To use programmatically, import `assembly_scraper_methods.py`, which contains the following methods:
    - `scrape_member_list(session)`: return a dict containing the list of assembly members in the relevant session (note that you must use the current session, as past sessions are unavailable on the website).
    - `scrape_bill_list_data(session)`: return a dict containing the list of bills voted on in the relevant session (here you may you use a past session).
    - `scrape_member_data(member_id, session)`: return a dict containing information about a given assembly member (note that member IDs are not guaranteed to be consistent across sessions).
    - `scrape_bill_data(bill_no, bill_id, id_master, session)`: return a dict containing information about a given bill, including the list of members who voted for or against it. Note that you must use all three identifying variables (this is just how the National Assembly website is built).
