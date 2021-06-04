from web3 import Web3
import datetime
from constants import abiPancake

PRIVATE_KEY = ""


web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
jesus = '0xD13B5203aB41965ac93AA0938223c15a257444B0'

minBet = 100000000000000000
baseUnit = 1000000000000000000
bnbRisk = 3

betPercent = 0.2

# initialBalance = 1104537757360386385
begin_time = datetime.datetime.now()


# if CALC_BET:
def calculate_bet():
    balance = web3.eth.getBalance(jesus)
    if balance * betPercent >= baseUnit * bnbRisk:
        return baseUnit * bnbRisk
    else:
        return int(balance * betPercent)


addrPancake = '0x516ffd7D1e0Ca40b1879935B2De87cb20Fc1124b'
contractPancake = web3.eth.contract(address=addrPancake, abi=abiPancake)


def place_bet(is_bear):
    nonce = web3.eth.getTransactionCount(jesus)
    print('placing bet ', ['bear' if is_bear else 'bull'])
    bet_config = {
        'gas': 160000,
        'chainId': 56,
        'from': jesus,
        'nonce': nonce,
        'value': calculate_bet()
    }
    if not is_bear:
        transaction = contractPancake.functions.betBull().buildTransaction(bet_config)
    else:
        transaction = contractPancake.functions.betBear().buildTransaction(bet_config)

    signed_txn = web3.eth.account.signTransaction(
        transaction, private_key=PRIVATE_KEY)
    resultTransanction = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
    print(resultTransanction)


def claim_winnings(ROUND_ID):
    if contractPancake.functions.claimable(ROUND_ID, jesus).call():
        print(' claiming')
        nonce = web3.eth.getTransactionCount(jesus)
        transaction = contractPancake.functions.claim(ROUND_ID).buildTransaction({
            'gas': 160000,
            'chainId': 56,
            'from': jesus,
            'nonce': nonce,
        })

        signed_txn = web3.eth.account.signTransaction(
            transaction, private_key=PRIVATE_KEY)
        resultTransanction = web3.eth.sendRawTransaction(
            signed_txn.rawTransaction)
        print(resultTransanction)

    else:
        print('not claimable')
