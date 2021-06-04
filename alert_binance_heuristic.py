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


result = utils.get_pancake_last_rounds(2, 0)
live_round = result[1]
starts_at = int(live_round['lockAt'])
should_close_at = starts_at + ROUND_DURATION
should_bet_at = should_close_at - TIME_WINDOW


while True:

    now = round(datetime.timestamp(datetime.now()), 0)
     
    if now >= should_close_at:
      result = utils.get_pancake_last_rounds(2, 0)
      live_round = result[1]
      starts_at = int(live_round['lockAt'])
      should_close_at = starts_at + ROUND_DURATION
      should_bet_at = should_close_at - TIME_WINDOW  
      time.sleep(1)
      continue

    print(now, should_bet_at, should_close_at)
    
    
    if now < should_bet_at:
      continue

    
    if current_active_round_id is None or current_active_round_id != live_round['id']:
      
      current_active_round_id = live_round['id']
      chainlink_price = utils.get_chainlink_last_round_price()
      
      if chainlink_price['age'] < CHAINLINK_MAXIMUM_AGE:

        binance_price = utils.get_binance_last_price()
        base_price_difference = abs(
            binance_price - chainlink_price['price'])/chainlink_price['price']

        if base_price_difference >= PRICE_MINIMUM_DIFFERENCE:
            print('\njust did a bet')
            # place_bet(bool(binance_price < chainlink_price['price']))
            # llamar función de juan
        else:
            print("\ndidn't did a bet")
      else:
        print("didnt did a bet")
    