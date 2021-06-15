import requests
import csv
from datetime import datetime
from datetime import timedelta
import time
import utils
from utils import get_claimable_rounds,append_dict_as_row
from test_bot import place_bet

options = {
    'time_window': 10,
    'round_duration': 300,
    'chainlink_age': 70,
    'difference_percentage': 0.00171115983509094
}

TIME_WINDOW = options['time_window']
# Average from 28/05/2021 to 31/05/2021
ROUND_DURATION = options['round_duration']
CHAINLINK_MAXIMUM_AGE = options['chainlink_age']
PRICE_MINIMUM_DIFFERENCE = options['difference_percentage']

current_active_round_id = None


result = utils.get_pancake_last_rounds(2, 0)
live_round = result[1]
starts_at = int(live_round['lockAt'])
should_close_at = starts_at + ROUND_DURATION
should_bet_at = should_close_at - TIME_WINDOW
checked_claimed = False

just_did_a_bet = 0

while True:

    now = round(datetime.timestamp(datetime.now()), 0)

    if now >= should_close_at:
        result = utils.get_pancake_last_rounds(2, 0)
        
        if len(result) == 0:
            print("At {} we didn't find rounds information".format(datetime.fromtimestamp(now)))
            continue
        
        live_round = result[1]
        starts_at = int(live_round['lockAt'])
        should_close_at = starts_at + ROUND_DURATION
        should_bet_at = should_close_at - TIME_WINDOW
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

        if chainlink_price['age'] < CHAINLINK_MAXIMUM_AGE:

            binance_price  = utils.get_binance_price_for_timestamp(should_bet_at)
            #binance_price = utils.get_binance_last_price()
            if binance_price < 0:
                print("At {} we didn't find binance price information".format(datetime.fromtimestamp(now)))
                continue

            base_price_difference = abs(
                binance_price - chainlink_price['price'])/chainlink_price['price']



            # price_diference_to_enter = (
            #     PRICE_MINIMUM_DIFFERENCE if just_did_a_bet == 0 else price_diference_to_enter + 0.001
            # )

            price_diference_to_enter=PRICE_MINIMUM_DIFFERENCE

            csv_row = {
                'round_id':next_round_id,
                "chainlink_price_age":chainlink_price['age'],
                'binance_price':binance_price,
                'chainlink_price':chainlink_price['price'],
                'price_difference':base_price_difference,
                'price_difference_toEnter':price_diference_to_enter,
                'position': 'bear' if bool(binance_price < chainlink_price['price']) else 'bull',
                'date_before_bet': datetime.timestamp(datetime.now())
                
            }


            if base_price_difference >= price_diference_to_enter:
                just_did_a_bet = just_did_a_bet + 1

                # here the bot is betting oposite to the heuristic if it bets more than twice in a row
                # if just_did_a_bet > 2:
                #     place_bet(bool(binance_price >
                #                    chainlink_price['price']))
                # else:
                place_bet(bool(binance_price < chainlink_price['price']))
                # llamar función de juan
                
             
                csv_row['consecutives_bets']=just_did_a_bet
                csv_row['decision']='place_bet'
            else:
          
     
                csv_row['consecutives_bets']=just_did_a_bet
                csv_row['decision']='small_price_difference'

                just_did_a_bet = 0
           
            append_dict_as_row(csv_row)

        else:
           
            price_diference_to_enter=PRICE_MINIMUM_DIFFERENCE
            
            csv_row = {
                'round_id':next_round_id,
                "chainlink_price_age":chainlink_price['age'],
                'binance_price':'undefined',
                'chainlink_price':'undefined',
                'price_difference':'undefined',
                'price_difference_toEnter':price_diference_to_enter,
                'position': 'undefined',
                'consecutives_bets':just_did_a_bet,
                'decision':'chainlink_price_too_old',
                'date_before_bet': datetime.timestamp(datetime.now())
            }


            append_dict_as_row(csv_row)

            just_did_a_bet = 0

