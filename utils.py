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

def append_remove_first(played_list, element):

    # element is a dict with
    # {
    #    round_id: xxxx,
    #    won: True      
    # }

    search = list(filter(lambda round: int(round['round_id']) == int(element['round_id']), played_list))
    if len(search) > 0:
        print("Warning, tried to append already existent result to list",element)
        return None
    
    if len(played_list) < 15:
        played_list.append(element)
    else:
        played_list.pop(0)
        played_list.append(element)





def get_last_bets_from_wallet(wallets, quantity):

    result = []
    query = """
       query{{
        users(where: {{address_in: {wallets} }}){{
            id
            address
            bets (first: {quantity}, orderBy: createdAt, orderDirection: desc) {{
                position
                createdAt
                claimed
                amount
                claimedAmount
                round {{
                    position
                    closePrice
                    id
                }}
            }}
        }}
    }}
    """

    
    real_query = query.format(
        quantity=quantity,
        wallets=str(wallets).replace("'",'"')
    )
    response = run_query(real_query)

        
    users = response['data']['users']
    for user in users:
        bets = user['bets']
        for bet in bets:
            if bet['round']['closePrice']:
                result.append({
                    'round_id' : bet['round']['id'],
                    'won' : bet['round']['position'] == bet['position']
                })
        
            
    result.sort(key=lambda x: int(x['round_id']))
    return result




def get_binance_last_price():
    url = 'https://api.binance.com/api/v3/ticker/price'
    try:
        response = requests.get(url, params={'symbol': 'BNBUSDT'}, timeout=5)
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
        response = requests.get(url,params=query_string, timeout=5)
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

            response = requests.get(url,params=query_string,  timeout=5)
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
        'https://api.thegraph.com/subgraphs/name/pancakeswap/prediction-v2', json={'query': query}, timeout=5)
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
                orderBy: startAt,
                orderDirection: desc
            ){{
                id
                epoch
                startAt
                lockAt
                lockPrice
                closeAt
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


def get_round_from_contract(round_id, web3_connection, contract):

    round = contract.functions.rounds(round_id).call()
    
    #lock_block_number = int(round[2])
    #lock_timestamp = web3_connection.eth.get_block(lock_block_number).timestamp
    #print(lock_block_number)

    return {
        'id': round[0],
        'epoch': round[0],
        'lockAt': round[2],
        'lockPrice': round[4],
        'closePrice': round[5],
        'totalAmount': round[8]
    }

def get_pancake_last_rounds_v2(web3_connection, contract):

    next_round_ID = int(contract.functions.currentEpoch().call())
    live_round_ID = next_round_ID - 1
    closed_round_ID = live_round_ID - 1

    next_round = get_round_from_contract(next_round_ID,web3_connection, contract)
    live_round = get_round_from_contract(live_round_ID,web3_connection, contract)
    closed_round = get_round_from_contract(closed_round_ID,web3_connection, contract)

    return [next_round, live_round, closed_round]


def get_bet_info_from_contract(round_id, wallet, web3_connection, contract):

    [position, amount, claimed] = contract.functions.ledger(round_id,wallet).call()

    result = {
        "id" : round_id,
        "played": amount > 0,
    }

    if result['played']:
        result['position'] = "Bear" if position else "Bull"   
        result['claimed'] = claimed 


    return result


def get_last_bets_from_contract(wallets, web3_connection, contract, quantity):

    result = []
    

    for wallet in wallets:
        [rounds, _,length] = contract.functions.getUserRounds(wallet,0,1000).call()
        filtered_rounds = rounds[-quantity:]
        for c_round in filtered_rounds:

            
            round_info = get_bet_result_from_contract(c_round, wallet, web3_connection, contract)
            result.append({
                'round_id' : c_round,
                'won': round_info['won'] if round_info['closed'] else False
            })
            
    
    ordered_result = sorted(result, key = lambda k: int(k['round_id']))
    return ordered_result[-quantity:]

def get_last_bets_from_contract_full(wallets, web3_connection, contract, quantity):

    result = []
    

    for wallet in wallets:
        [rounds, _, length] = contract.functions.getUserRounds(wallet,0,1000).call()
        for c_round in rounds:

            round_info = get_bet_result_from_contract(c_round, wallet, web3_connection, contract)
            result.append(round_info)
        
    
    ordered_result = sorted(result, key = lambda k: int(k['id']))
    return ordered_result


def get_bet_result_from_contract(round_id,wallet,web3_connection,contract):

    round_info = get_round_from_contract(round_id, web3_connection, contract)
    bet_info = get_bet_info_from_contract(round_id, wallet, web3_connection, contract)

    round_is_closed = round_info['closePrice'] != 0
    round_was_played = bet_info['played']

    result = {
        'id': round_id,
        'closed': round_is_closed,
        'played': round_was_played
    }
    
    if round_was_played:
        result['position'] = bet_info['position']
        result['claimed'] = bet_info['claimed']

    if round_was_played and round_is_closed:
        if round_info['closePrice'] < round_info['lockPrice']:
            round_position = "Bear"
        elif round_info['closePrice'] > round_info['lockPrice']:
            round_position = "Bull"
        else:
            round_position = "House"
        
        result['won'] = round_position == bet_info['position'] 

    return result




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
        'id', 'position', 'startAt', 'startHash', 'lockAt', 'lockPrice', 'closeAt', 'closePrice',
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
                filter(lambda x: x['position'] == x['round']['position'] or x['round']['position'] is None, bets))
            print(filterd_bets)  
            return filterd_bets
    except Exception as e:
        print(e)
        return []

def get_claimable_rounds_v2(wallet, web3_connection, contract):

    try:
        result = get_last_bets_from_contract_full([wallet], web3_connection, contract, 1000)
        if len(result) < 1:
            return []
        else:
            filterd_bets = list(
                filter(lambda x: x['closed'] and x['won'] and not x['claimed'], result))
            print(filterd_bets)  
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

def date_to_timestamp(date_string, use_utc=True):

    try:
        result_date = datetime.strptime(date_string, '%Y-%m-%d')
        if use_utc:
            result_date = pytz.utc.localize(result_date)
        
        return int(datetime.timestamp(result_date))

    except Exception as e:
        print(e)
        sys.exit(2)


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
    try: 
        result = {
            'spearman' : scipy.stats.spearmanr(x_axis,y_axis),
            'pearson' : scipy.stats.pearsonr(x_axis,y_axis),
        }
        return result
    except Exception as e:
        print(e)
        return {
            'spearman' : [0,0],
            'pearson' : [0,0]
        }


# In case we need to do tests, this is the minimum bet that can be placed
# minBet = 100000000000000000

def calculate_bet(wallet, web3_connection, max_bnb, max_percentage):
    baseUnit = 1000000000000000000
    balance = web3_connection.eth.getBalance(wallet)
    if balance * max_percentage >= baseUnit * max_bnb:
        return int(baseUnit * max_bnb)
    else:
        return int(balance * max_percentage)


def place_bet(is_bear,wallet,private_key,web3_connection, contract, max_bnb, max_percentage,round_id):
    nonce = web3_connection.eth.getTransactionCount(wallet)
    print('placing bet ', ['bear' if is_bear else 'bull'])
    amount = calculate_bet(wallet,web3_connection,max_bnb,max_percentage)
    bet_config = {
        'gas': 160000,
        'chainId': 56,
        'from': wallet,
        'nonce': nonce,
        'value': amount
    }
    if not is_bear:
        transaction = contract.functions.betBull(round_id).buildTransaction(bet_config)
    else:
        transaction = contract.functions.betBear(round_id).buildTransaction(bet_config)

    signed_txn = web3_connection.eth.account.signTransaction(
        transaction, private_key=private_key)
    resultTransanction = web3_connection.eth.sendRawTransaction(signed_txn.rawTransaction)
    print(resultTransanction)


def claim_winnings(round_id, wallet, private_key, web3_connection, contract):
    if contract.functions.claimable(round_id, wallet).call():
        print(' claiming')
        nonce = web3_connection.eth.getTransactionCount(wallet)
        print('nonce:',nonce)
        transaction = contract.functions.claim([round_id]).buildTransaction({
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


def lost_too_close_num(array,current):

    bets_calm_window = 10
    bets_panic_window = 6
    panic_distance = 3
    calm_distance = 6


    if len(array) >= 2:

        last = int(array[-1])
        previous = int(array[-2])

        if last - previous <= panic_distance and int(current) - last <= bets_panic_window:
            return 0.008

        elif last - previous <= panic_distance and bets_calm_window > int(current) - last:
            return 0.003

        elif last - previous > panic_distance and int(current) - last <= bets_panic_window:
            return 0.001

        elif calm_distance > last - previous > panic_distance and bets_calm_window > int(current) - last:
            return 0.0005

    return 0

def calculate_effectivity(played_array):

    min = 5
    size =  10
    if len(played_array) <= min:
        return 0
    
    
    won = list(filter(lambda x: x['won'], played_array[-size:]))

    
    effectivity = len(won)/len(played_array[-size:])
    #7 35 1
    
    # if effectivity < 0.6:
    #     return 0.003
    # elif effectivity < 0.65:
    #     return 0.0027
    # elif effectivity < 0.70:
    #     return 0.0010
    # elif effectivity < 0.75:
    #     return 0.0007
    # elif effectivity < 0.80:
    #     return 0.0005
    

    if effectivity < 0.5:
        return 0.007
    elif effectivity < 0.6:
        return 0.0035
    elif effectivity < 0.7:
        return 0.001
    
    
    return 0


# from constants import (
#     pancake_address,
#     abi_pancake,
#     network_provider
 
# )

# from config import (
#     bot_max_bnb,
#     bot_max_percentage

# )

# from web3.middleware import geth_poa_middleware

# web3 = Web3(Web3.HTTPProvider(network_provider))
# web3.middleware_onion.inject(geth_poa_middleware, layer=0)
# contractPancake = web3.eth.contract(address=pancake_address, abi=abi_pancake)

# # played_bets_array = get_last_bets_from_contract(['0x0Dfd5dC37bD6c207dBFA13fb9aCA2cD08126B42C','0xe4F27d5C68760955d3CD9dd2Ca7514c3d562E57D'], web3, contractPancake, 20)
# # print(played_bets_array)

# x = get_pancake_last_rounds_v2(web3, contractPancake)
# print(x)
# #x = get_bet_result_from_contract(19239, "0xe4F27d5C68760955d3CD9dd2Ca7514c3d562E57D", web3, contractPancake)
# #print(x)

# # Bear = True
# # x = place_bet(True, 'wallet', 'private_key', web3, contractPancake, bot_max_bnb, bot_max_percentage, 354)
# # print(x)

