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
        chainlink_price = utils.get_chainlink_last_round_price()

        if chainlink_price['age'] < CHAINLINK_MAXIMUM_AGE:

            binance_price = utils.get_binance_last_price()
            base_price_difference = abs(
                binance_price - chainlink_price['price'])/chainlink_price['price']



            PRICE_DIFFERENCE_TO_ENTER = (
                PRICE_MINIMUM_DIFFERENCE if just_did_a_bet == 0 else PRICE_DIFFERENCE_TO_ENTER + 0.001
            )

            csv_row = {
                'round_id':current_active_round_id,
                "chainlink_price_age":chainlink_price['age'],
                'binance_price':binance_price,
                'chainlink_price':chainlink_price['price'],
                'price_difference':base_price_difference,
                'price_difference_toEnter':PRICE_DIFFERENCE_TO_ENTER,
                'position': 'bear' if bool(binance_price < chainlink_price['price']) else 'bull',
                
            }


            if base_price_difference >= PRICE_DIFFERENCE_TO_ENTER:
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
           
            
            csv_row = {
                'round_id':current_active_round_id,
                "chainlink_price_age":chainlink_price['age'],
                'binance_price':'undefined',
                'chainlink_price':'undefined',
                'price_difference':'undefined',
                'price_difference_toEnter':PRICE_DIFFERENCE_TO_ENTER,
                'position': 'undefined',
                'consecutives_bets':just_did_a_bet,
                'decision':'chainlink_price_too_old'
            }


            append_dict_as_row(csv_row)

            just_did_a_bet = 0

