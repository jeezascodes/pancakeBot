from datetime import datetime
from web3 import Web3
import requests

web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))


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
    addr = '0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE'
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


def get_claimable_rounds():
    query = """query{
            users(where: {address: "0xf764B5925e530C5D5939C4d47CDCABB8F1D63bD0"}){
            id
            address
            bets (where: {claimed: false}) {
            position
            claimed
            round {
                position
                id
            }
            }
            }
            }"""

    result = run_query(query)

    if len(result['data']['users']) < 1:
        return []
    else:
        bets = result['data']['users'][0]['bets']
        filterd_bets = list(
            filter(lambda x: x['position'] == x['round']['position'], bets))
        return filterd_bets


def get_if_user_has_open_bet():
    query = """query{
            users(where: {address: "0xf764B5925e530C5D5939C4d47CDCABB8F1D63bD0"}){
            id
            address
            bets (first: 1, orderBy: createdAt, orderDirection: desc) {
            position
            claimed
            round {
                position
                id
            }
            }
            }
            }"""

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


# def get_pending_transactions():
#     web3.eth.filter('pending')
