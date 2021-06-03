from web3 import Web3
import csv
import requests
import copy


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
            new_element['before_lock_window'] = int(new_element['lockAt']) - seconds_left
            result.append(new_element)
            

        # If there where less than 'step' elements, there is no
        # need to do more requests, else do new request skipping already
        # fetched elements
        fetched_elements += len(response['data']['rounds'])
        need_extra_request = step == len(response['data']['rounds'])
    
    return result


MIN_TIMESTAMP = 1622178000
MAX_TIMESTAMP = 1622523600
PREVIOUS_WINDOW = 5
FILE = 'pancake_data.csv'

collected_data = get_rounds_from_pancake(MIN_TIMESTAMP,MAX_TIMESTAMP, seconds_left=PREVIOUS_WINDOW)
all_fields = ROUND_FIELDS + ['before_lock_window']
file = open(FILE, 'w', newline='')
# writing the data into the file
with file:
    writer = csv.DictWriter(file, fieldnames=all_fields)
    writer.writeheader()
    writer.writerows(collected_data)