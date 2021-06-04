from web3 import Web3
import json
from decimal import *
from optparse import OptionParser
import datetime

PRIVATE_KEY = "8a2685788a9dfb16c3e7192737078c7733d54ee66531e31312ba0602aa0d79d2"

parser = OptionParser()
parser.add_option("--type",
                  dest="betType",
                  type="string",
                  default='',
                  help="type of bet (bear,bull)")
parser.add_option("--calc_bet",
                  dest="calcBet",
                  action="store_true",
                  default=False,
                  help="calculate Bet according to Balance")
parser.add_option("--claim",
                  dest="epothClaim",
                  type="int",
                  default=0,
                  help="Epoch to Claim")

(options, args) = parser.parse_args()

BET_TYPE = options.betType
CALC_BET = options.calcBet
EPOCH_CLAIM = options.epothClaim


web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed.binance.org/'))
juan = '0x0C4dFeAb618b3344d21070049b32CAAb80131577'
jesus = '0xD13B5203aB41965ac93AA0938223c15a257444B0'

minBet = 100000000000000000
baseUnit = 1000000000000000000
bnbRisk = 1

betPercent = 0.2

# initialBalance = 1104537757360386385
begin_time = datetime.datetime.now()

nonce = web3.eth.getTransactionCount(jesus)

if CALC_BET:
    balance = web3.eth.getBalance(jesus)

    if balance * betPercent >= baseUnit * bnbRisk:
        bet = baseUnit * bnbRisk
    else:
        bet = int(balance * betPercent)
else:
    bet = minBet

abiPancake = '[{"inputs":[{"internalType":"contract AggregatorV3Interface","name":"_oracle","type":"address"},{"internalType":"address","name":"_adminAddress","type":"address"},{"internalType":"address","name":"_operatorAddress","type":"address"},{"internalType":"uint256","name":"_intervalBlocks","type":"uint256"},{"internalType":"uint256","name":"_bufferBlocks","type":"uint256"},{"internalType":"uint256","name":"_minBetAmount","type":"uint256"},{"internalType":"uint256","name":"_oracleUpdateAllowance","type":"uint256"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":true,"internalType":"uint256","name":"currentEpoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"BetBear","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":true,"internalType":"uint256","name":"currentEpoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"BetBull","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":true,"internalType":"uint256","name":"currentEpoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"Claim","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"}],"name":"ClaimTreasury","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"epoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"blockNumber","type":"uint256"},{"indexed":false,"internalType":"int256","name":"price","type":"int256"}],"name":"EndRound","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"epoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"blockNumber","type":"uint256"},{"indexed":false,"internalType":"int256","name":"price","type":"int256"}],"name":"LockRound","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"epoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"minBetAmount","type":"uint256"}],"name":"MinBetAmountUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":true,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"epoch","type":"uint256"}],"name":"Pause","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"account","type":"address"}],"name":"Paused","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"epoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"rewardRate","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"treasuryRate","type":"uint256"}],"name":"RatesUpdated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"epoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"rewardBaseCalAmount","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"rewardAmount","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"treasuryAmount","type":"uint256"}],"name":"RewardsCalculated","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"epoch","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"blockNumber","type":"uint256"}],"name":"StartRound","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"epoch","type":"uint256"}],"name":"Unpause","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"address","name":"account","type":"address"}],"name":"Unpaused","type":"event"},{"inputs":[],"name":"TOTAL_RATE","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"adminAddress","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"betBear","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"betBull","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"bufferBlocks","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"epoch","type":"uint256"}],"name":"claim","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"claimTreasury","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"epoch","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"claimable","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"currentEpoch","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"executeRound","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"genesisLockOnce","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"genesisLockRound","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"genesisStartOnce","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"genesisStartRound","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"user","type":"address"},{"internalType":"uint256","name":"cursor","type":"uint256"},{"internalType":"uint256","name":"size","type":"uint256"}],"name":"getUserRounds","outputs":[{"internalType":"uint256[]","name":"","type":"uint256[]"},{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"intervalBlocks","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"},{"internalType":"address","name":"","type":"address"}],"name":"ledger","outputs":[{"internalType":"enum BnbPricePrediction.Position","name":"position","type":"uint8"},{"internalType":"uint256","name":"amount","type":"uint256"},{"internalType":"bool","name":"claimed","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"minBetAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"operatorAddress","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"oracleLatestRoundId","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"oracleUpdateAllowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"pause","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"paused","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"epoch","type":"uint256"},{"internalType":"address","name":"user","type":"address"}],"name":"refundable","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"rewardRate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"rounds","outputs":[{"internalType":"uint256","name":"epoch","type":"uint256"},{"internalType":"uint256","name":"startBlock","type":"uint256"},{"internalType":"uint256","name":"lockBlock","type":"uint256"},{"internalType":"uint256","name":"endBlock","type":"uint256"},{"internalType":"int256","name":"lockPrice","type":"int256"},{"internalType":"int256","name":"closePrice","type":"int256"},{"internalType":"uint256","name":"totalAmount","type":"uint256"},{"internalType":"uint256","name":"bullAmount","type":"uint256"},{"internalType":"uint256","name":"bearAmount","type":"uint256"},{"internalType":"uint256","name":"rewardBaseCalAmount","type":"uint256"},{"internalType":"uint256","name":"rewardAmount","type":"uint256"},{"internalType":"bool","name":"oracleCalled","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"_adminAddress","type":"address"}],"name":"setAdmin","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_bufferBlocks","type":"uint256"}],"name":"setBufferBlocks","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_intervalBlocks","type":"uint256"}],"name":"setIntervalBlocks","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_minBetAmount","type":"uint256"}],"name":"setMinBetAmount","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_operatorAddress","type":"address"}],"name":"setOperator","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"_oracle","type":"address"}],"name":"setOracle","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_oracleUpdateAllowance","type":"uint256"}],"name":"setOracleUpdateAllowance","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_rewardRate","type":"uint256"}],"name":"setRewardRate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"_treasuryRate","type":"uint256"}],"name":"setTreasuryRate","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"treasuryAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"treasuryRate","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"unpause","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"uint256","name":"","type":"uint256"}],"name":"userRounds","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
addrPancake = '0x516ffd7D1e0Ca40b1879935B2De87cb20Fc1124b'
contractPancake = web3.eth.contract(address=addrPancake, abi=abiPancake)


def place_bet(is_bear):
    print('placing bet ', ['bear' if is_bear else 'bull'])
    bet_config = {
        'gas': 160000,
        'chainId': 56,
        'from': jesus,
        'nonce': nonce,
        'value': bet
    }
    if not is_bear:
        transaction = contractPancake.functions.betBull().buildTransaction(bet_config)
    else:
        transaction = contractPancake.functions.betBear().buildTransaction(bet_config)

    signed_txn = web3.eth.account.signTransaction(
        transaction, private_key=PRIVATE_KEY)
    resultTransanction = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
    print(resultTransanction)


# if BET_TYPE == 'bear':

#     print("beting bear: ", bet / baseUnit)

#     transaction = contractPancake.functions.betBear().buildTransaction({
#         'gas': 160000,
#         # 'gasPrice': web3.toWei('1', 'gwei'),
#         'chainId': 56,
#         'from': jesus,
#         'nonce': nonce,
#         'value': bet
#     })

#     signed_txn = web3.eth.account.signTransaction(
#         transaction, private_key=PRIVATE_KEY)
#     resultTransanction = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
#     print(resultTransanction)
#     # print(web3.toText(resultTransanction))

# elif BET_TYPE == "bull":

#     print("beting bull: ", bet / baseUnit)

#     transaction = contractPancake.functions.betBull().buildTransaction({
#         'gas': 160000,
#         # 'gasPrice': web3.toWei('1', 'gwei'),
#         'chainId': 56,
#         'from': jesus,
#         'nonce': nonce,
#         'value': bet
#     })

#     signed_txn = web3.eth.account.signTransaction(
#         transaction, private_key=PRIVATE_KEY)
#     resultTransanction = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
#     print(resultTransanction)
#     # print(web3.toText(resultTransanction))

# else:
#     print('not beting')
#     if EPOCH_CLAIM != 0:
#         # 5452
#         if contractPancake.functions.claimable(EPOCH_CLAIM, jesus).call():
#             print(' claiming')
#             transaction = contractPancake.functions.claim(EPOCH_CLAIM).buildTransaction({
#                 'gas': 160000,
#                 # 'gasPrice': web3.toWei('1', 'gwei'),
#                 'chainId': 56,
#                 'from': jesus,
#                 'nonce': nonce,
#             })

#             signed_txn = web3.eth.account.signTransaction(
#                 transaction, private_key=PRIVATE_KEY)
#             resultTransanction = web3.eth.sendRawTransaction(
#                 signed_txn.rawTransaction)
#             print(resultTransanction)

#         else:
#             print('not claimable')


print(datetime.datetime.now() - begin_time)
