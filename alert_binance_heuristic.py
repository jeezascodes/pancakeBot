import requests
from datetime import datetime
from datetime import timedelta
import time
import utils
from utils import get_claimable_rounds
from test_bot import place_bet

options = {
    'time_window': 10,
    'round_duration': 300,
    'chainlink_age': 70,
    'difference_percentage': 0.00350240113364098
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

            PRICE_MINIMUM_DIFFERENCE = (
                0.00450240113364098 if just_did_a_bet == 0 else 0.00450240113364098 + 0.001
            )

            print(PRICE_MINIMUM_DIFFERENCE)

            if base_price_difference >= PRICE_MINIMUM_DIFFERENCE:
                just_did_a_bet += 1
                print('\njust did a bet', just_did_a_bet)
                print(PRICE_MINIMUM_DIFFERENCE)
                print('TIME_WINDOW', TIME_WINDOW)
                # here the bot is betting oposite to the heuristic if it bets more than twice in a row
                if just_did_a_bet > 2:
                    place_bet(bool(binance_price >
                                   chainlink_price['price']))
                else:
                    place_bet(bool(binance_price < chainlink_price['price']))
                # llamar función de juan
            else:
                print("\ndidn't did a bet")
                just_did_a_bet = 0
        else:
            print("didnt did a bet")
            just_did_a_bet = 0
