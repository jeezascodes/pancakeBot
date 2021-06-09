from web3 import Web3
import csv
import requests
import copy
from optparse import OptionParser
import utils
    

def run_query(query):
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/pancakeswap/prediction', json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(
            request.status_code, query))



def get_bets_from_pancake(min_t, max_t, wallet, step=1000):

    result = []
    query = """
       query{{
        users(where: {{address: "{wallet}"}}){{
            id
            address
            createdAt
            updatedAt
            block
            totalBets
            totalBNB
            bets (first: {quantity}, skip: {skip}, where: {{createdAt_gt: {min_date}, createdAt_lt: {max_date} }} orderBy: createdAt, orderDirection: asc) {{
                position
                createdAt
                claimed
                amount
                claimedAmount
                round {{
                    position
                    id
                    totalBets
                    totalAmount
                    bullBets
                    bullAmount
                    bearBets
                    bearAmount
                }}
            }}
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
            min_date=min_t,
            max_date=max_t,
            wallet=wallet
            )
        )

        bets = response['data']['users'][0]['bets']

        for bet in bets:
            new_element = copy.deepcopy(bet)
            new_element['round_id']= new_element['round']['id']
            new_element['round_position'] = new_element['round']['position']
            new_element['round_totalBets'] = new_element['round']['totalBets']
            new_element['round_totalAmount'] = new_element['round']['totalAmount']
            new_element['round_bullBets'] = new_element['round']['bullBets']
            new_element['round_bullAmount'] = new_element['round']['bullAmount']
            new_element['round_bearBets'] = new_element['round']['bearBets']
            new_element['round_bearAmount'] = new_element['round']['bearAmount']
            new_element.pop('round',None)
            result.append(new_element)
            

        # If there where less than 'step' elements, there is no
        # need to do more requests, else do new request skipping already
        # fetched elements
        fetched_elements += len(bets)
        need_extra_request = step == len(bets)
    
    return result


parser = OptionParser()
utils.add_date_options_to_parser(parser)
parser.add_option("--wallet_id",
                  dest="wallet_id",
                  help="Wallet that will be queried",
                    )
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the bets will be dumped",
                  default="bets_data.csv")

(options, args) = parser.parse_args()


MIN_TIMESTAMP, MAX_TIMESTAMP = utils.process_date_options(parser, options)
FILE = options.output_file

collected_data = get_bets_from_pancake(MIN_TIMESTAMP,MAX_TIMESTAMP,options.wallet_id)

# writing the data into the file
if len(collected_data) > 0:
    file = open(FILE, 'w', newline='')
    with file:
        writer = csv.DictWriter(file, fieldnames=list(collected_data[0].keys()))
        writer.writeheader()
        writer.writerows(collected_data)