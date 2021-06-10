import csv
from collections import OrderedDict
import numpy
from datetime import datetime
from datetime import timedelta
import requests
import time
from optparse import OptionParser
import utils

    
def load_data_from_csv(file, min_t, max_t):
    result = []
    with open(file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if min_t <= int(row['lockAt']) < max_t:
                result.append(row)
    
    print("loaded {count} rounds inside interval from {file}".format(count=len(result), file=file))
    return result
    



# Verify Parameters
parser = OptionParser()
utils.add_date_options_to_parser(parser)
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the results of every bet will be dumped",
                  default="binance_model_bets_detail.csv")
parser.add_option("--input_file",
                  dest="input_file",
                  help="csv file with the rounds information",
                  default="binance_forecast_result.csv")
parser.add_option("--wallet_initial",
                  dest="wallet_initial",
                  type="float",
                  help="wallet initial amount in BNB",
                  default=1.0)
parser.add_option("--bet_max_bnb",
                  dest="bet_max_bnb",
                  type="float",
                  help="maximal bet allowed in BNB",
                  default=1.0)
parser.add_option("--bet_percentage",
                  dest="bet_percentage",
                  type="float",
                  help="percentage of portfolio that will be used in any bet",
                  default=0.2)
parser.add_option("--difference_percentage",
                  dest="difference_percentage",
                  type="float",
                  help="minimal difference between binance and chainlink to enter in a bet",
                  default=0.00350240113364098)
parser.add_option("--chainlink_age",
                  dest="chainlink_age",
                  type="int",
                  help="maximal age (seconds) for a chainlink price to enter in a bet",
                  default=70)
parser.add_option("--consecutive_errors",
                  dest="consecutive_errors",
                  type="int",
                  help="consecutive error that should be logged",
                  default=2)



(options, args) = parser.parse_args()

MIN_TIMESTAMP, MAX_TIMESTAMP = utils.process_date_options(parser, options)
PORTFOLIO_PERCENTAGE = options.bet_percentage
PORTFOLIO_INITIAL_AMOUNT = options.wallet_initial
MAXIMUM_BET = options.bet_max_bnb
DIFFERENCE_MINIMUM = options.difference_percentage
MAXIMUM_AGE = options.chainlink_age
FAILURE_MAXIMUM = options.consecutive_errors
ORIGIN_CSV_FILE = options.input_file
OUTPUT_CSV_FILE = options.output_file


failure_log = []
played_rounds = []
round_data = load_data_from_csv(ORIGIN_CSV_FILE,MIN_TIMESTAMP,MAX_TIMESTAMP)
portfolio_total = PORTFOLIO_INITIAL_AMOUNT
consecutive_errors = []

for p_round in round_data:

    if p_round['chainlink_price'] == 'N/A':
        continue
    
    binance_difference = float(p_round['binance_difference'])
    chainlink_price_age = int(p_round['chainlink_price_age'])

    # If this happens, we bet on the round
    if binance_difference >= DIFFERENCE_MINIMUM and chainlink_price_age < MAXIMUM_AGE:


        bet_amount = portfolio_total * PORTFOLIO_PERCENTAGE
        if bet_amount > MAXIMUM_BET:
            bet_amount = MAXIMUM_BET

        won_bet = p_round['binance_position'] == p_round['position']
        payout = 0
        if p_round['position'] == 'Bull':
            payout = (float(p_round['bearAmount'])/float(p_round['bullAmount']))
        else:
            payout = (float(p_round['bullAmount'])/float(p_round['bearAmount']))

        bet_info = {
            'id': p_round['id'],
            'bet' : bet_amount,
            'status' : 'won' if won_bet else 'lost',
            'earnings' : payout * bet_amount if won_bet else -bet_amount,
            'payout' : payout
        }
        played_rounds.append(bet_info)

        if won_bet:
            portfolio_total += payout * bet_amount
            consecutive_errors = []
        else:
            portfolio_total -= bet_amount
            consecutive_errors.append(p_round['id'])

        if len(consecutive_errors) == FAILURE_MAXIMUM:
            failure_log.append(consecutive_errors)
            consecutive_errors = []


won = len(list(filter(lambda x: x['status'] == 'won', played_rounds)))
lost = len(played_rounds) - won
print("Portfolio Status: Started With {} BNB - Ended with {} BNB".format(PORTFOLIO_INITIAL_AMOUNT,portfolio_total))
print("Won {} rounds and, lost {} rounds".format(won,lost))
print("Success rate: {}%".format(round((won / len(played_rounds))* 100,2)))
print("Lost {} consecutive bets {} times".format(FAILURE_MAXIMUM,len(failure_log)))

# writing the data into the file
file = open(OUTPUT_CSV_FILE, 'w', newline='')
if len(played_rounds) > 0:
    fieldnames = list(played_rounds[0].keys())
    with file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(played_rounds)