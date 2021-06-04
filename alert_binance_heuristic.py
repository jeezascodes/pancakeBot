import requests
from datetime import datetime
from datetime import timedelta
import pprint
import time
import tkinter
from tkinter import *
import utils
from optparse import OptionParser
from sys import stdout
from test_bot import place_bet


# Verify Parameters
parser = OptionParser()
parser.add_option("--time_window",
                  dest="time_window",
                  type="int",
                  default=15,
                  help="seconds before lock when live round will be checked and window will be showed")
parser.add_option("--round_duration",
                  dest="round_duration",
                  type="int",
                  default=300,
                  help="estimated seconds for a round to close since its lock time")
parser.add_option("--difference_percentage",
                  dest="difference_percentage",
                  type="float",
                  help="minimal difference between binance and chainlink to enter in a bet",
                  default=0.00050240113364098)
parser.add_option("--chainlink_age",
                  dest="chainlink_age",
                  type="int",
                  help="maximal age (seconds) for a chainlink price to enter in a bet",
                  default=70)


(options, args) = parser.parse_args()

TIME_WINDOW = options.time_window
# Average from 28/05/2021 to 31/05/2021
ROUND_DURATION = options.round_duration
CHAINLINK_MAXIMUM_AGE = options.chainlink_age
PRICE_MINIMUM_DIFFERENCE = options.difference_percentage

current_active_round_id = None
round_processed = False

while True:

    # if current_active_round_id is None:
    result = utils.get_pancake_last_rounds(2, 0)
    live_round = result[1]

    now = round(datetime.timestamp(datetime.now()), 0)
    starts_at = int(live_round['lockAt'])
    should_close_at = starts_at + ROUND_DURATION
    should_wake_up_at = should_close_at - TIME_WINDOW

    if now >= should_close_at:
        time.sleep(1)
        continue

    # Si el ronda es nuevo vemos por cuanto tiempo dormir
    if current_active_round_id != live_round['id']:
        print("Nueva ronda 'live' {}".format(live_round['id']))
        current_active_round_id = live_round['id']
        if now <= should_wake_up_at:
            seconds_left = should_wake_up_at - now
            print("Faltan {} segundos para revisar la ronda {}".format(
                seconds_left, live_round['id']))
            round_processed = False
            time.sleep(seconds_left)
            continue
        elif now >= should_wake_up_at + 5:
            seconds_left = should_close_at - now
            print("Leimos la ronda {} muy tarde, esperare {} segundos por el proximo".format(
                live_round['id'], seconds_left))
            round_processed = True
            time.sleep(seconds_left if seconds_left >= 0 else 1)
            continue

    chainlink_price = utils.get_chainlink_last_round_price()
    if chainlink_price['age'] < CHAINLINK_MAXIMUM_AGE:

        binance_price = utils.get_binance_last_price()
        base_price_difference = abs(
            binance_price - chainlink_price['price'])/chainlink_price['price']

        print(base_price_difference)
        if base_price_difference >= PRICE_MINIMUM_DIFFERENCE:
            print('just did a bet')
            # place_bet(bool(binance_price < chainlink_price['price']))
            # llamar función de juan

        else:
            seconds_left = should_close_at - now
            time.sleep(seconds_left if seconds_left > 0 else 5)
    else:
        seconds_left = should_close_at - now
        time.sleep(seconds_left if seconds_left > 0 else 5)
