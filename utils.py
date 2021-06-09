from datetime import datetime
from datetime import timedelta
import pytz
from web3 import Web3
import requests
import os
from csv import DictWriter
from constants import wallet, network_provider, chainlink_addres
import sys

web3 = Web3(Web3.HTTPProvider(network_provider))


def get_binance_last_price():
    url = 'https://api.binance.com/api/v3/ticker/price'
    response = requests.get(url, params={'symbol': 'BNBUSDT'})
    # FALTA VALIDAR PEO DEL WEIGHT Y LOS LIMITES
    data = response.json()
    return float(data['price'])


def get_chainlink_last_round_price():
    web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed1.ninicoin.io/'))
    abi = (
        '[{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},'
        '{"inputs":[],"name":"description","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},'
        '{"inputs":[{"internalType":"uint80","name":"_roundId","type":"uint80"}],"name":"getRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},'
        '{"inputs":[{"internalType":"uint80","name":"_id","type":"uint80"}],"name":"getPreviousAnswer","outputs":[{"internalType":"int256","name":"price","type":"int256"}],"stateMutability":"view","type":"function"},'
        '{"inputs":[],"name":"latestRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},'
        '{"inputs":[],"name":"version","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
    )
    addr = chainlink_addres
    contract = web3.eth.contract(address=addr, abi=abi)
    data = contract.functions.latestRoundData().call()
    now = round(datetime.timestamp(datetime.now()), 0)
    return {
        'roundId': data[0],
        'price': int(data[1]) / 10**8,
        'age': now - int(data[2])
    }


def run_query(query):
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/pancakeswap/prediction', json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(
            request.status_code, query))


def get_pancake_last_rounds(first, skip):

    query = """
        query {{
            rounds(
                first: {first},
                skip: {skip},
                orderBy: epoch,
                orderDirection: desc
            ){{
                id
                epoch
                startAt
                lockAt
                lockPrice
                endAt
                closePrice
                totalBets
                totalAmount
                bullBets
                bullAmount
                bearBets
                bearAmount
                position
            }}
        }}
    """

    result = run_query(query.format(first=first, skip=skip))
    return result['data']['rounds']


def get_rounds_from_pancake_using_range(min_t, max_t, step=1000):

    ROUND_FIELDS = [
        'id', 'position', 'startAt', 'startBlock', 'startHash', 'lockAt', 'lockBlock',
        'lockHash', 'lockPrice', 'endAt', 'endBlock', 'endHash', 'closePrice',
        'totalBets', 'totalAmount', 'bullBets', 'bullAmount', 'bearBets', 'bearAmount'
    ]

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

        result += response['data']['rounds']
        
        # If there where less than 'step' elements, there is no
        # need to do more requests, else do new request skipping already
        # fetched elements
        fetched_elements += len(response['data']['rounds'])
        need_extra_request = step == len(response['data']['rounds'])
    
    return result


def get_claimable_rounds():
    query = """query{{
            users(where: {{address: "{currentWallet}"}}){{
            id
            address
            bets (where: {{claimed: false}}) {{
            position
            claimed
            round {{
                position
                id
            }}
            }}
            }}
            }}""".format(currentWallet=wallet)

    result = run_query(query)

    if len(result['data']['users']) < 1:
        return []
    else:
        bets = result['data']['users'][0]['bets']
        filterd_bets = list(
            filter(lambda x: x['position'] == x['round']['position'], bets))
        return filterd_bets


def get_if_user_has_open_bet():
    query = """query{{
            users(where: {{address: "{currentWallet}"}}){{
            id
            address
            bets (first: 1, orderBy: createdAt, orderDirection: desc) {{
            position
            claimed
            amount
            round {{
                position
                id
            }}
            }}
            }}
            }}""".format(currentWallet=wallet)

    result = run_query(query)
    if len(result['data']['users']) < 1:
        return False
    else:
        bets = result['data']['users'][0]['bets']
        return not bool(bets[0]['round']['position'])


def get_wallet_balance(wallet):
    try:
        return web3.eth.getBalance(wallet)
    except:
        print('got error from web3 try again')



def process_date_options(parser,parse_options):

    result = []
    if parse_options.begin_timestamp: 

        if not parse_options.end_timestamp:
            parser.error(" both begin_timestamp and --end_timestamp are required")
            sys.exit(2)
        
        try:
            result.append(int(parse_options.begin_timestamp))
            result.append(int(parse_options.end_timestamp))
        except:
            parser.error("timestamps with wrong format")

    else:

        if not parse_options.begin_date or not parse_options.end_date:
            parser.error(" --begin_date and --end_date are required")
            sys.exit(2)
        
        try:
            begin_date = datetime.strptime(parse_options.begin_date, '%Y-%m-%d')
            end_date = datetime.strptime(parse_options.end_date, '%Y-%m-%d') + timedelta(1)
        except:
            parser.error(" --begin_date and --end_date should be YYYY-MM-DD")
            sys.exit(2)

        if parse_options.use_utc:
            begin_date = pytz.utc.localize(begin_date)
            end_date = pytz.utc.localize(end_date)
        
        result.append(int(datetime.timestamp(begin_date)))
        result.append(int(datetime.timestamp(end_date)))

    return result


def add_date_options_to_parser(parser):

    parser.add_option("--begin_date", dest="begin_date",
                  help="minimum date of a round lock to be considered, use '%Y-%m-%d' format")
    parser.add_option("--end_date", dest="end_date", 
                    help="maximum date of a round lock to be considered, use '%Y-%m-%d' format")
    parser.add_option("--use_utc", action="store_true",dest="use_utc", 
                    help="Use the given dates on UTC")
    parser.add_option("--begin_timestamp", dest="begin_timestamp", 
                    help="begin timestamp (overrides begin_date)")
    parser.add_option("--end_timestamp", dest="end_timestamp", 
                    help="end timestamp (overrides end_date)")


def get_trend(numbers):
    rows = []
    total_numbers = len(numbers)
    currentValueNumber = 1
    n = 0
    while n < len(numbers):
        rows.append({'row': currentValueNumber, 'number': numbers[n]})
        currentValueNumber += 1
        n += 1
    sumLines = 0
    sumNumbers = 0
    sumMix = 0
    squareOfs = 0
    for k in rows:
        sumLines += k['row']
        sumNumbers += k['number']
        sumMix += k['row']*k['number']
        squareOfs += k['row'] ** 2
    a = (total_numbers * sumMix) - (sumLines * sumNumbers)
    b = (total_numbers * squareOfs) - (sumLines ** 2)
    c = a/b
    return c


# def get_pending_transactions():
#     web3.eth.filter('pending')
def append_dict_as_row(dict_of_elem,file_name=wallet[0:8]+'_result.csv'):
    # el nombre del archivo de salida son las primeros 8 caracteres del wallet
    # mas result.csv

    if os.path.exists(file_name):
        append_write = 'a' # append if already exists
    else:
        append_write = 'w' # make a new file if not
       
    # Open file in append mode
    field_names=dict_of_elem.keys()
    with open(file_name, append_write, newline='') as write_obj:
        # Create a writer object from csv module
        dict_writer = DictWriter(write_obj, fieldnames=field_names)
        # Add dictionary as wor in the csv
        if append_write =='w':
            dict_writer.writeheader()

        dict_writer.writerow(dict_of_elem)