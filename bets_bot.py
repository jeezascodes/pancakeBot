import requests
import csv
from datetime import datetime
from datetime import timedelta
import time
import utils
import sys
import os
from dotenv import load_dotenv
from web3 import Web3
from utils import get_claimable_rounds,append_dict_as_row, place_bet

from constants import (
    pancake_address,
    abi_pancake,
    network_provider

)
from config import (
    seconds_before_lock,
    round_duration,
    spearman_min_value,
    min_percentage_difference,
    max_percentage_difference,
    chainlink_price_max_age,
    bot_max_bnb,
    bot_max_percentage
)


current_active_round_id = None
result = utils.get_pancake_last_rounds(2, 0)
live_round = result[1]
starts_at = int(live_round['lockAt'])
should_close_at = starts_at + round_duration
should_bet_at = should_close_at - seconds_before_lock
checked_claimed = False
just_did_a_bet = 0


load_dotenv()
WALLET = os.environ.get('WALLET')
PRIVATE_KEY = os.environ.get('PRIVATE_KEY')

if WALLET is None or PRIVATE_KEY is None:
    print("This script cannot run without a defined .env file that contains 'WALLET' and 'PRIVATE_KEY' entries")
    sys.exit(2)

web3 = Web3(Web3.HTTPProvider(network_provider))
contractPancake = web3.eth.contract(address=pancake_address, abi=abi_pancake)

if max_percentage_difference is None:
    print("Error: This bot needs at least the 'max_percentage_difference' variable in config to work")
    sys.exit(2)

if not min_percentage_difference is None:
    print(
        "Warning, this bot will bet on rounds using a difference from {} to {}".format(
            min_percentage_difference,
            max_percentage_difference
            )
    )

if not spearman_min_value is None:
    print("Warning, this bot will bet using a spearman coeffcient of {}".format(spearman_min_value))


while True:

    now = round(datetime.timestamp(datetime.now()), 0)

    if now >= should_close_at:
        result = utils.get_pancake_last_rounds(2, 0)
        
        if len(result) == 0:
            print("At {} we didn't find rounds information".format(datetime.fromtimestamp(now)))
            continue
        
        live_round = result[1]
        starts_at = int(live_round['lockAt'])
        should_close_at = starts_at + round_duration
        should_bet_at = should_close_at - seconds_before_lock
        time.sleep(1)
        if current_active_round_id is None or current_active_round_id != live_round['id']:
            print('\n')
            print('New block ', live_round['id'])
            checked_claimed = False
        continue

    if now < should_bet_at:
        continue

    if current_active_round_id is None or current_active_round_id != live_round['id']:

        current_active_round_id = live_round['id']
        next_round_id = int(current_active_round_id) + 1
        chainlink_price = utils.get_chainlink_last_round_price()
        if chainlink_price['roundId'] == 0:
            print("At {} we didn't find chainlink price information".format(datetime.fromtimestamp(now)))
            continue

        if chainlink_price['age'] <= chainlink_price_max_age:

            minute_data  = utils.get_binance_minute_data_for_timestamp(should_bet_at)
            
            if len(minute_data) == 0:
                print("At {} we didn't find binance price information".format(datetime.fromtimestamp(now)))
                continue
            
            minute_metrics = utils.calculate_metrics_for_array([float(elem['price']) for elem in minute_data])
            binance_price = minute_metrics['close']
            base_price_difference = abs(
                binance_price - chainlink_price['price'])/chainlink_price['price']
            decision=''
            consecutives_bets=0

            price_is_ok = base_price_difference >= max_percentage_difference
            if not min_percentage_difference is None:
                price_is_ok = min_percentage_difference <= base_price_difference < max_percentage_difference

            spearman_is_ok = True
            if not spearman_min_value is None:
                current_spearman, p_value = utils.calculate_data_direction(minute_data)
                bet_is_bear = binance_price <= chainlink_price['price']
                spearman_is_ok = (
                    (bet_is_bear and current_spearman <= -1*spearman_min_value) or 
                    (not bet_is_bear and current_spearman >= spearman_min_value)
                )


            if price_is_ok and spearman_is_ok:
                just_did_a_bet = just_did_a_bet + 1

                place_bet(
                    binance_price < chainlink_price['price'],
                    WALLET,
                    PRIVATE_KEY,
                    web3,
                    contractPancake,
                    bot_max_bnb,
                    bot_max_percentage
                )
                # print("DISQUE APOSTABA")
                consecutives_bets=just_did_a_bet
                decision='place_bet'
            elif price_is_ok and not spearman_is_ok:
                decision='spearman_not_ok'
                just_did_a_bet = 0
            else:
                decision='price_not_ok'
                just_did_a_bet = 0
           
            csv_row = {
                'round_id':next_round_id,
                "chainlink_price_age":chainlink_price['age'],
                'binance_price':binance_price,
                'chainlink_price':chainlink_price['price'],
                'price_difference':base_price_difference,
                'position': 'bear' if binance_price < chainlink_price['price'] else 'bull',
                'consecutives_bets':consecutives_bets,
                'decision':decision,
                'date_before_bet': datetime.timestamp(datetime.now()),
                'should_bet_at': should_bet_at             
            }
            append_dict_as_row(csv_row,WALLET)

        else:
            csv_row = {
                'round_id' : next_round_id,
                "chainlink_price_age":chainlink_price['age'],
                'binance_price':'undefined',
                'chainlink_price':chainlink_price['price'],
                'price_difference':'undefined',
                'position': 'undefined',
                'consecutives_bets':just_did_a_bet,
                'decision':'chainlink_price_too_old',
                'date_before_bet': datetime.timestamp(datetime.now()),
                'should_bet_at': should_bet_at
            }
            append_dict_as_row(csv_row,WALLET)
            just_did_a_bet = 0

