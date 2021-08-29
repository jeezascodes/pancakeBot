from web3 import Web3
import csv
import requests
import copy
from optparse import OptionParser
import utils
import collections
import pytz
from datetime import datetime
import os
    

def run_query(query):
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/pancakeswap/prediction', json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(
            request.status_code, query))



def get_rounds_from_pancake_between_dates(min_t,max_t, step=1000):
    result = []
    query = """
        query{{
            rounds(first: {step}, skip: {skip}, where: {{lockAt_gte: {min_date}, lockAt_lt: {max_date} }}){{
                id
            }}
        }}
    """

    fetched_elements = 0
    need_extra_request = True
    while need_extra_request:

        response = run_query(query.format(
            step=step,
            skip=fetched_elements,
            min_date=min_t,
            max_date=max_t
            )
        )

        result += response['data']['rounds']
        
        # If there where less than 'step' elements, there is no
        # need to do more requests, else do new request skipping already
        # fetched elements
        fetched_elements += len(response['data']['rounds'])
        need_extra_request = step == len(response['data']['rounds'])
    
    return result
        

def get_bet_wallets_from_pancake_between_rounds(min_r,max_r, round_step=5):
    result = []
    query = """
        query{{
            bets(first: {step}, skip: {skip}, where: {{round_gte: "{min_round}" round_lte: "{max_round}"}}){{
                user {{
                address
                }}
            }}
        }}
    """

    

    
    min_round = min_r
    bets_steps = 1000

    print("Fetching from {} to {}".format(min_r, max_r))
    while min_round < max_r:
        max_round = min_round + round_step if min_round + round_step < max_r else max_r
        fetched_elements = 0
        need_extra_request = True
        while need_extra_request:
            response = run_query(query.format(
                step=bets_steps,
                skip=fetched_elements,
                min_round=min_round,
                max_round=max_round
                )
            )

            result += [x['user']['address'] for x in response['data']['bets']]
            # If there where less than 'step' elements, there is no
            # need to do more requests, else do new request skipping already
            # fetched elements
            fetched_elements += len(response['data']['bets'])
            need_extra_request = bets_steps == len(response['data']['bets'])
        
        min_round = max_round + 1
        
    return result

        
def count_dict_to_array(count_dict, date):

    return [
        {'timestamp': date,
        'datetime_utc': datetime.fromtimestamp(date, pytz.utc),
        'datetime_local': datetime.fromtimestamp(date),
        'address' : elem,
        'count' : count_dict[elem]
        }
        for elem in count_dict.keys()
    ]



parser = OptionParser()
utils.add_date_options_to_parser(parser)
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the bets will be dumped",
                  default="bets_per_day_data.csv")
parser.add_option("--start_from_date",
                  dest="start_from_date",
                  help="start from a given date if the file has results already calculated",
                  type="string")



(options, args) = parser.parse_args()


[min_timestamp, max_timestamp] = utils.process_date_options(parser, options)
out_file = options.output_file

if options.start_from_date:
    start_from_timestamp = utils.date_to_timestamp(options.start_from_date , options.use_utc)


first_date = min_timestamp if not options.start_from_date else start_from_timestamp + 86400
results = []

FIELDS = ['timestamp','datetime_utc','datetime_local','address','count']

append_write = 'a' if os.path.exists(out_file) else 'w'
csv_file = open(out_file, append_write, newline='')
writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
if append_write == 'w':
    writer.writeheader()

while first_date < max_timestamp :

    last_date =  first_date + 86400
    rounds = get_rounds_from_pancake_between_dates(first_date, last_date)
    rounds = [int(x['id']) for x in rounds]
    first_round = min(rounds)
    last_round = max(rounds)
    addresses = get_bet_wallets_from_pancake_between_rounds(first_round, last_round, 10)
    count_dict = collections.Counter(addresses)

    writer.writerows(count_dict_to_array(count_dict, first_date))
    first_date =  last_date
    

