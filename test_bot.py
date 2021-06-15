from web3 import Web3
import datetime
from constants import abiPancake
import os
from dotenv import load_dotenv
from constants import wallet, pancake_address, network_provider


load_dotenv()

PRIVATE_KEY = os.environ.get("PRIVATE_KEY")


web3 = Web3(Web3.HTTPProvider(network_provider))

minBet = 100000000000000000
baseUnit = 1000000000000000000
bnbRisk = 1.5

betPercent = 0.2

# initialBalance = 1104537757360386385
begin_time = datetime.datetime.now()


# if CALC_BET:
def calculate_bet():
    balance = web3.eth.getBalance(wallet)
    if balance * betPercent >= baseUnit * bnbRisk:
        return int(baseUnit * bnbRisk)
    else:
        return int(balance * betPercent)


addrPancake = pancake_address
contractPancake = web3.eth.contract(address=addrPancake, abi=abiPancake)


def place_bet(is_bear):
    nonce = web3.eth.getTransactionCount(wallet)
    print('placing bet ', ['bear' if is_bear else 'bull'])
    bet_config = {
        'gas': 160000,
        'chainId': 56,
        'from': wallet,
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
    if contractPancake.functions.claimable(ROUND_ID, wallet).call():
        print(' claiming')
        nonce = web3.eth.getTransactionCount(wallet)
        print('nonce:',nonce)
        transaction = contractPancake.functions.claim(ROUND_ID).buildTransaction({
            'gas': 160000,
            'chainId': 56,
            'from': wallet,
            'nonce': nonce,
        })

        signed_txn = web3.eth.account.signTransaction(
            transaction, private_key=PRIVATE_KEY)
        resultTransanction = web3.eth.sendRawTransaction(
            signed_txn.rawTransaction)
        print(resultTransanction)
        print('despues del claim')

    else:
        print('not claimable')
