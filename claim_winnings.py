import sys
import os
from dotenv import load_dotenv
from utils import get_claimable_rounds_v2, claim_winnings
import time
from web3 import Web3
from constants import network_provider, pancake_address, abi_pancake
from web3.middleware import geth_poa_middleware

# Verify ENV

load_dotenv()
WALLET = os.environ.get('WALLET')
PRIVATE_KEY = os.environ.get('PRIVATE_KEY')

if WALLET is None or PRIVATE_KEY is None:
    print("This script cannot run without a defined .env file that contains 'WALLET' and 'PRIVATE_KEY' entries")
    sys.exit(2)


web3 = Web3(Web3.HTTPProvider(network_provider))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
contractPancake = web3.eth.contract(address=pancake_address, abi=abi_pancake)


while True:
    claimable_rounds = get_claimable_rounds_v2(WALLET,web3,contractPancake)
    print(claimable_rounds)
    if len(claimable_rounds) > 1:
        for c_round in claimable_rounds:
            claim_winnings(int(c_round['round']['id']),WALLET,PRIVATE_KEY,web3,contractPancake)
            time.sleep(20)
    elif len(claimable_rounds) == 1:
        c_round=claimable_rounds[0]
        claim_winnings(int(c_round['round']['id']),WALLET,PRIVATE_KEY,web3,contractPancake)
       
    time.sleep(30)
