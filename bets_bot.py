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
    spearman_value,
    spearman_mode,
    spearman_max_difference,
    min_percentage_difference,
    max_percentage_difference,
    chainlink_price_max_age,
    bot_max_bnb,
    bot_max_percentage,
    failed_round_penalty,
    maximum_consecutive_bets,
    trauma_mode
)


def check_spearman(spearman_coefficient, bet_is_bear, price_difference, spearman_mode, spearman_value, spearman_max_difference):

    if not spearman_max_difference is None and price_difference > spearman_max_difference:
        return True
    
    if spearman_mode == "conservative":
        return (
            (bet_is_bear and spearman_coefficient < spearman_value) or
            (not bet_is_bear and spearman_coefficient > spearman_value * -1)
        )
    else:
        return (
            (bet_is_bear and spearman_coefficient <= spearman_value * -1) or
            (not bet_is_bear and spearman_coefficient >= spearman_value)
        )


current_active_round_id = None
result = utils.get_pancake_last_rounds(3, 0)
live_round = result[1]
starts_at = int(live_round['lockAt'])
should_close_at = starts_at + round_duration
should_bet_at = should_close_at - seconds_before_lock
checked_claimed = False
just_did_a_bet = 0
last_bet_bear = False
last_bet_id = None
won_last_bet = True
last_bet_difference = 0
lost_bets_array = []

load_dotenv()
WALLET = os.environ.get('WALLET')
PRIVATE_KEY = os.environ.get('PRIVATE_KEY')

if WALLET is None or PRIVATE_KEY is None:
    print("This script cannot run without a defined .env file that contains 'WALLET' and 'PRIVATE_KEY' entries")
    sys.exit(2)

web3 = Web3(Web3.HTTPProvider(network_provider))
contractPancake = web3.eth.contract(address=pancake_address, abi=abi_pancake)

if min_percentage_difference is None:
    print("Error: This bot needs at least the 'min_percentage_difference' variable in config to work")
    sys.exit(2)

if not max_percentage_difference is None:
    print(
        "Warning, this bot will bet on rounds using a difference from {} to {}".format(
            min_percentage_difference,
            max_percentage_difference
            )
    )

if not spearman_value is None:
    if spearman_mode != 'conservative' and spearman_mode != 'aggressive':
        print("Error: if spearman_value is defined, spearman_mode must be provided as aggressive or conservative")   
        sys.exit(2)
    
    print("Warning, this bot will bet using a spearman coeffcient of {} in {} mode".format(spearman_value, spearman_mode))

if not spearman_max_difference is None:
    print("Warning, this bot will bet applying spearman to bets betweeen {} and {}".format(min_percentage_difference, spearman_max_difference))

if not maximum_consecutive_bets is None:
    print("Warning, this bot will bet only for a maximum of {} consecutive rounds".format(maximum_consecutive_bets))

if not failed_round_penalty is None:
    print("Warning, this bot will apply an extra {} penalty on minimum percentage difference if the last round was lost".format(failed_round_penalty))  

if trauma_mode:
    print("Warning, this bot will apply an extra penalty if we have lost two rounds in the last 10 rounds")


while True:

    now = round(datetime.timestamp(datetime.now()), 0)

    if now >= should_close_at:
        result = utils.get_pancake_last_rounds(3, 0)
        
        if len(result) == 0:
            print("At {} we didn't find rounds information".format(datetime.fromtimestamp(now)))
            time.sleep(1)
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

        last_closed_round = result[2]
        # If i didnt validate the last bet when the round was live, because the chainlink price
        # was too old, i validate if we won here
        if int(last_closed_round['id']) == last_bet_id:
            last_lock_price = float(last_closed_round['lockPrice'])
            last_close_price = float(last_closed_round['closePrice'])
            if last_bet_bear and last_lock_price > last_close_price:
                won_last_bet = True
            elif not last_bet_bear and last_lock_price < last_close_price:
                won_last_bet = True
            else:
                won_last_bet = False
                if not last_bet_id in lost_bets_array:
                    lost_bets_array.append(last_bet_id)

        current_active_round_id = live_round['id']
        next_round_id = int(current_active_round_id) + 1
        chainlink_price = utils.get_chainlink_last_round_price()
        
        if chainlink_price['roundId'] == 0:
            print("At {} we didn't find chainlink price information".format(datetime.fromtimestamp(now)))
            continue

        if chainlink_price['age'] <= chainlink_price_max_age:
            
            # Checking if the last bet was won or lost
            if just_did_a_bet > 0:
                if last_bet_bear and chainlink_price['price'] < float(live_round['lockPrice']):
                    won_last_bet = True
                elif not last_bet_bear and chainlink_price['price'] > float(live_round['lockPrice']):
                    won_last_bet = True
                else:
                    won_last_bet = False
                    lost_bets_array.append(last_bet_id)

            minute_data  = utils.get_binance_minute_data_for_timestamp(should_bet_at)
            
            if len(minute_data) == 0:
                print("At {} we didn't find binance price information".format(datetime.fromtimestamp(now)))
                continue
            
            minute_metrics = utils.calculate_metrics_for_array([float(elem['price']) for elem in minute_data])
            binance_price = minute_metrics['close']
            base_price_difference = abs(
                binance_price - chainlink_price['price'])/chainlink_price['price']
            decision=''

            real_minimum = min_percentage_difference
            if not failed_round_penalty is None and not won_last_bet:
                real_minimum = real_minimum + (failed_round_penalty * just_did_a_bet)

            if trauma_mode:
                other_minimum = min_percentage_difference + utils.lost_too_close_num(lost_bets_array, next_round_id)
                print(other_minimum, lost_bets_array[-2:], next_round_id)
                real_minimum = max(real_minimum, other_minimum)

            

            price_is_ok = base_price_difference >= real_minimum
            
            if not max_percentage_difference is None:
                price_is_ok = real_minimum <= base_price_difference < max_percentage_difference

            spearman_is_ok = True
            if not spearman_value is None:
                current_spearman, _  = utils.calculate_data_direction(minute_data)['spearman']
                bet_is_bear = binance_price <= chainlink_price['price']
                spearman_is_ok = check_spearman(
                    current_spearman, 
                    bet_is_bear, 
                    base_price_difference, 
                    spearman_mode, 
                    spearman_value, 
                    spearman_max_difference)
                

            if price_is_ok and spearman_is_ok:
                just_did_a_bet = just_did_a_bet + 1

                if not maximum_consecutive_bets is None and just_did_a_bet > maximum_consecutive_bets:
                    decision='too_many_consecutive_bets'
                else:
                    last_bet_bear = binance_price < chainlink_price['price']
                    last_bet_id = next_round_id
                    last_bet_difference = base_price_difference

                    place_bet(
                        binance_price < chainlink_price['price'],
                        WALLET,
                        PRIVATE_KEY,
                        web3,
                        contractPancake,
                        bot_max_bnb,
                        bot_max_percentage
                    )
                    #print("DISQUE APOSTABA")
                    decision='place_bet'
            elif price_is_ok and not spearman_is_ok:
                decision='spearman_not_ok'
                just_did_a_bet = 0
            else:
                decision='price_not_ok'
                if real_minimum > min_percentage_difference:
                    decision = 'price_not_ok_penalty_applied_' + str(real_minimum)
                
                just_did_a_bet = 0
           
            csv_row = {
                'round_id':next_round_id,
                "chainlink_price_age":chainlink_price['age'],
                'binance_price':binance_price,
                'chainlink_price':chainlink_price['price'],
                'price_difference':base_price_difference,
                'position': 'bear' if binance_price < chainlink_price['price'] else 'bull',
                'consecutives_bets':just_did_a_bet,
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

