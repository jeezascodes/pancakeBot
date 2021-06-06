from web3 import Web3
import csv
import requests
import copy
from datetime import timedelta
from datetime import datetime
from optparse import OptionParser

ROUND_FIELDS = [
'id', 'position', 'startAt', 'startBlock', 'startHash', 'lockAt', 'lockBlock',
'lockHash', 'lockPrice', 'endAt', 'endBlock', 'endHash', 'closePrice',
'totalBets', 'totalAmount', 'bullBets', 'bullAmount', 'bearBets', 'bearAmount'
]
    

def run_query(query):
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/pancakeswap/prediction', json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(
            request.status_code, query))



def get_rounds_from_pancake(min_t, max_t, step=1000, seconds_left=10):

    result = []
    query = """
        query {{
            rounds(
                first: {quantity},
                skip: {skip},
                where: {{
                    lockAt_gte: {min_t},
                    lockAt_lt: {max_t}
                }},
                orderBy: id,
                orderDirection: asc
            ){{
                {fields_list}
            }}
        }}
    """
    
    fetched_elements = 0
    need_extra_request = True
    while need_extra_request:

        new_elements = 0
        response = run_query(query.format(
            quantity=step,
            skip=fetched_elements,
            min_t=min_t,
            max_t=max_t,
            fields_list="\n".join(ROUND_FIELDS)
            )
        )

        for element in response['data']['rounds']:
            new_element = copy.deepcopy(element)
            new_element['before_lock_window'] = int(new_element['lockAt']) + 300 - seconds_left
            result.append(new_element)
            

        # If there where less than 'step' elements, there is no
        # need to do more requests, else do new request skipping already
        # fetched elements
        fetched_elements += len(response['data']['rounds'])
        need_extra_request = step == len(response['data']['rounds'])
    
    return result


parser = OptionParser()
parser.add_option("--begin_date", dest="min_date",
                  help="minimum date of a round lock to be considered, use '%Y-%m-%d' format")
parser.add_option("--end_date", dest="max_date",
                  help="maximum date of a round lock to be considered, use '%Y-%m-%d' format")
parser.add_option("--window_before_close",
                  dest="window_before_close",
                  type="int",
                  help="Seconds before the close of the round where the calculations will be made",
                  default=10)
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the prices will be dumped",
                  default="pancake_data.csv")

(options, args) = parser.parse_args()

if not options.min_date or not options.max_date:
    parser.error(" --begin_date and --end_date are required")
    sys.exit(2)

try:
    min_date = datetime.strptime(options.min_date, '%Y-%m-%d')
    max_date = datetime.strptime(options.max_date, '%Y-%m-%d') + timedelta(1)
except:
    parser.error(" --begin_date and --end_date should be YYYY-MM-DD")
    sys.exit(2)


MIN_TIMESTAMP = int(datetime.timestamp(min_date))
MAX_TIMESTAMP = int(datetime.timestamp(max_date))

PREVIOUS_WINDOW = options.window_before_close
FILE = options.output_file

collected_data = get_rounds_from_pancake(MIN_TIMESTAMP,MAX_TIMESTAMP, seconds_left=PREVIOUS_WINDOW)
all_fields = ROUND_FIELDS + ['before_lock_window']
file = open(FILE, 'w', newline='')
# writing the data into the file
with file:
    writer = csv.DictWriter(file, fieldnames=all_fields)
    writer.writeheader()
    writer.writerows(collected_data)