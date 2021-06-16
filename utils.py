from datetime import datetime
from datetime import timedelta
import pytz
from web3 import Web3
import requests
import os
from csv import DictWriter
from constants import (
    network_provider,
    chainlink_address
)
import sys
import statistics
import scipy.stats


def get_binance_last_price():
    url = 'https://api.binance.com/api/v3/ticker/price'
    try:
        response = requests.get(url, params={'symbol': 'BNBUSDT'})
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print(e)
        return -1


def calculate_bet_difference_from_volatitly(price_stdev_percentage, aggresive_diff, middle_diff, conservative_diff):

    # This calculations were created using the data from 03/06/2021 to 08/06/2021
    #
    #  MIN          0.000047450425045
    #  P0           0.000274273396124
    #  P1           0.000354791285285
    #  P2           0.000419999056739
    #  P3           0.000494032674363
    #  P4           0.000573124868205
    #  P5           0.000667372998241
    #  P6           0.000780954449481
    #  P7           0.000947973935181
    #  P8           0.001240594065159
    #  MAX (P9)     0.008617263673595

    P9_MIN = 0.001240594065159
    P8_MIN = 0.000947973935181

    
    if price_stdev_percentage <= P8_MIN:
        return aggresive_diff
    elif P8_MIN < price_stdev_percentage <= P9_MIN:
        return middle_diff
    else:
        return conservative_diff





def get_binance_price_for_timestamp(timestamp):

     # Given a timestamp, we are going to look for the latest transaction
     # before the timestamp, binance require the timestamps with milliseconds
     # precission so we add three zeroes, one second before the timestamp should
     # be enough, i am using 5 seconds just for precaution
     end_timestamp_binance = int(timestamp) * 1000
     start_timestamp_binace = end_timestamp_binance - 5000

     url = 'https://api.binance.com/api/v3/aggTrades'
     query_string = {
        'symbol' : 'BNBUSDT',
        'startTime': start_timestamp_binace,
        'endTime': end_timestamp_binance,
        'limit' : 1
     }
     
     try: 
        response = requests.get(url,params=query_string)
        data = response.json()
        if len(data) > 0:
            return float(data[0]['p'])
        else:
            return -1
     except Exception as e:
         print(e)
         return -1


def calculate_metrics_for_array(data):

    try:
        min_value = min(data)
        max_value = max(data)
        
        return {
            'stdev': statistics.stdev(data),
            'mean': statistics.mean(data),
            'min': min(data),
            'max': max(data),
            'price_variation': (max_value - min_value) / min_value, 
            'median': statistics.median(data),
            'open': data[-1],
            'close': data[0]
        }

    except Exception as e:
        print(e)
        print("problem here")
        return {
            'stdev': 0,
            'mean': 0,
            'min': 0,
            'max': 0,
            'price_variation': 0,
            'median': 0,
            'open': 0,
            'close': 0
        }
        


def get_binance_minute_data_for_timestamp(timestamp):

     # Given a timestamp, we are going to look for the latest transaction
     # before the timestamp, binance require the timestamps with milliseconds
     # precission so we add three zeroes
     end_timestamp_binance = int(timestamp) * 1000
     start_timestamp_binace = end_timestamp_binance - 60000
     result = []

     url = 'https://api.binance.com/api/v3/aggTrades'
     query_string = {
        'symbol' : 'BNBUSDT',
        'startTime': start_timestamp_binace,
        'endTime': end_timestamp_binance,
        'limit' : 1000
     }
     
     try: 
        
        fetched_elements = 0
        need_extra_request = True
        while need_extra_request:

            response = requests.get(url,params=query_string)
            data = response.json()
            data.reverse()
            result += [{'price': el['p'], 'timestamp': el['T']} for el in data]
            
            fetched_elements += len(data)
            need_extra_request = 1000 == len(data)
            if need_extra_request:
                query_string['endTime'] = int(data[-1]['T'])-1
            
        return result

     except Exception as e:
         print(e)
         return []




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
    addr = chainlink_address
    contract = web3.eth.contract(address=addr, abi=abi)
    try:
        data = contract.functions.latestRoundData().call()
        now = round(datetime.timestamp(datetime.now()), 0)
        return {
            'roundId': data[0],
            'price': int(data[1]) / 10**8,
            'age': now - int(data[2])
        }
    except Exception as e:
        print(e)
        return {
            'roundId': 0,
            'price': 0,
            'age': 100000
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

    try:
        result = run_query(query.format(first=first, skip=skip))
        return result['data']['rounds']
    except Exception as e:
        print(e)
        return []

    

# Este query dejara de funcionar si el mercado c
def get_round_bets_at_timestamp(round_number, timestamp):

    bets = []
    result = {
        'bearAmount' : 0,
        'bearBets' : 0,
        'bullAmount' : 0,
        'bullBets' : 0,
        'totalAmount' : 0,
        'totalBets' : 0,
    }
    query = """
        query{{
            bets(first: {quantity}, skip: {skip}, where: {{round: "{round}", createdAt_lte: {timestamp} }})
            {{
                amount
                position
                createdAt
                updatedAt
            }}
        }}
    """

    fetched_elements = 0
    need_extra_request = True
    while need_extra_request:

        response = run_query(query.format(
            quantity=1000,
            skip=fetched_elements,
            round=round_number,
            timestamp=timestamp
            )
        )

        bets += response['data']['bets']
        fetched_elements += len(response['data']['bets'])
        need_extra_request = 1000 == len(response['data']['bets'])

    for bet in bets:

        if bet['position'] == "Bear":
            result['bearAmount'] += float(bet['amount'])
            result['bearBets'] += 1
        else:
            result['bullAmount'] += float(bet['amount'])
            result['bullBets'] += 1
        
        result['totalAmount'] += float(bet['amount'])
        result['totalBets'] += 1

    return result


    



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


def get_claimable_rounds(wallet):

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

    try:
        result = run_query(query)

        if len(result['data']['users']) < 1:
            return []
        else:
            bets = result['data']['users'][0]['bets']
            filterd_bets = list(
                filter(lambda x: x['position'] == x['round']['position'], bets))
            return filterd_bets
    except Exception as e:
        print(e)
        return []

def get_if_user_has_open_bet(wallet):
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


def append_dict_as_row(dict_of_elem,wallet):
    csv_name = wallet[0:8]+'_result.csv'

    if os.path.exists(csv_name):
        append_write = 'a' # append if already exists
    else:
        append_write = 'w' # make a new file if not
       
    # Open file in append mode
    field_names=dict_of_elem.keys()
    with open(csv_name, append_write, newline='') as write_obj:
        # Create a writer object from csv module
        dict_writer = DictWriter(write_obj, fieldnames=field_names)
        # Add dictionary as wor in the csv
        if append_write =='w':
            dict_writer.writeheader()

        dict_writer.writerow(dict_of_elem)


def calculate_data_direction(data):

    ordered_data = sorted(data, key = lambda k: int(k['timestamp']))
    x_axis = [int(el['timestamp']) for el in ordered_data]
    y_axis = [float(el['price']) for el in ordered_data]
    #correlation, p_value = scipy.stats.spearmanr(x_axis,y_axis)

    # I will use values greater than equal to 0.6 to consider something
    # important enough

    return scipy.stats.spearmanr(x_axis,y_axis)


# In case we need to do tests, this is the minimum bet that can be placed
# minBet = 100000000000000000

def calculate_bet(wallet, web3_connection, max_bnb, max_percentage):
    baseUnit = 1000000000000000000
    balance = web3_connection.eth.getBalance(wallet)
    if balance * max_percentage >= baseUnit * max_bnb:
        return int(baseUnit * max_bnb)
    else:
        return int(balance * max_percentage)


def place_bet(is_bear,wallet,private_key,web3_connection, contract, max_bnb, max_percentage):
    nonce = web3_connection.eth.getTransactionCount(wallet)
    print('placing bet ', ['bear' if is_bear else 'bull'])
    bet_config = {
        'gas': 160000,
        'chainId': 56,
        'from': wallet,
        'nonce': nonce,
        'value': calculate_bet(wallet,web3_connection,max_bnb,max_percentage)
    }
    if not is_bear:
        transaction = contract.functions.betBull().buildTransaction(bet_config)
    else:
        transaction = contract.functions.betBear().buildTransaction(bet_config)

    signed_txn = web3_connection.eth.account.signTransaction(
        transaction, private_key=private_key)
    resultTransanction = web3_connection.eth.sendRawTransaction(signed_txn.rawTransaction)
    print(resultTransanction)


def claim_winnings(round_id, wallet, private_key, web3_connection, contract):
    if contract.functions.claimable(round_id, wallet).call():
        print(' claiming')
        nonce = web3_connection.eth.getTransactionCount(wallet)
        print('nonce:',nonce)
        transaction = contract.functions.claim(round_id).buildTransaction({
            'gas': 160000,
            'chainId': 56,
            'from': wallet,
            'nonce': nonce,
        })

        signed_txn = web3_connection.eth.account.signTransaction(
            transaction, private_key=private_key)
        resultTransanction = web3_connection.eth.sendRawTransaction(
            signed_txn.rawTransaction)
        print(resultTransanction)
        print('despues del claim')
    else:
        print('not claimable')
