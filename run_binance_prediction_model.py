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
parser.add_option("--min_difference_percentage",
                  dest="min_difference_percentage",
                  type="float",
                  help="minimal difference between binance and chainlink to enter in a bet")
parser.add_option("--max_difference_percentage",
                  dest="max_difference_percentage",
                  type="float",
                  help="maximal difference between binance and chainlink to enter in a bet",
                  default=0.00171115983509094)
parser.add_option("--chainlink_age",
                  dest="chainlink_age",
                  type="int",
                  help="maximal age (seconds) for a chainlink price to enter in a bet",
                  default=70)
parser.add_option("--spearman_min",
                  dest="spearman_min",
                  type="float",
                  help="minimum spearm coefficient to be accepted")
parser.add_option("--follow_public",
                  dest="follow_public",
                  action="store_true",
                  help="use public proxy to filtrate")                  
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
    
    public_is_ok = True
    if options.follow_public:
        public_position = 'Bear' if float(p_round['lock_bear_amount']) >= float(p_round['lock_bull_amount']) else 'Bull'
        public_is_ok = public_position == p_round['binance_position']

    difference_is_ok = binance_difference >= options.max_difference_percentage
    if not options.min_difference_percentage is None :
        minimum = options.min_difference_percentage
        maximum = options.max_difference_percentage
        difference_is_ok = minimum <= binance_difference < maximum

    spearman_is_ok = True
    if not options.spearman_min is None:
        round_spearman = float(p_round['spearman_coefficient'])
        spearman_is_ok = (
            (p_round['binance_position'] == 'Bear' and round_spearman <= -1*options.spearman_min) or 
            (p_round['binance_position'] == 'Bull' and round_spearman >= options.spearman_min)
        )
    
    age_is_ok = chainlink_price_age <= MAXIMUM_AGE

    
    
    if public_is_ok and difference_is_ok and spearman_is_ok and age_is_ok: 


        bet_amount = portfolio_total * PORTFOLIO_PERCENTAGE
        if bet_amount > MAXIMUM_BET:
            bet_amount = MAXIMUM_BET

        won_bet = p_round['binance_position'] == p_round['position']
        bull = float(p_round['bullAmount']) + (bet_amount if p_round['binance_position'] == "Bull" else 0)
        bear = float(p_round['bearAmount']) + (bet_amount if p_round['binance_position'] == "Bear" else 0)
        if p_round['position'] == 'Bull':
            payout = bear/bull
        else:
            payout = bull/bear

        bet_info = {
            'id': p_round['id'],
            'lock_date' : datetime.fromtimestamp(int(p_round['lockAt'])).strftime('%Y-%m-%d %H:%M:%S'),
            'bet' : bet_amount,
            'status' : 'won' if won_bet else 'lost',
            'earnings' : payout * bet_amount if won_bet else -bet_amount,
            'winning_payout' : payout,
            'bet_position': p_round['binance_position'],
            'price_diffence': binance_difference,
        }
        
        played_rounds.append(bet_info)

        if won_bet:
            portfolio_total += payout * bet_amount
            consecutive_errors = []
        else:
            portfolio_total -= bet_amount
            consecutive_errors.append(p_round['id'])
        
        bet_info['wallet_balance'] = portfolio_total

        if len(consecutive_errors) == FAILURE_MAXIMUM:
            failure_log.append(consecutive_errors)
            consecutive_errors = []


won_rounds = list(filter(lambda x: x['status'] == 'won', played_rounds))
won = len(won_rounds)
lost = len(played_rounds) - won
average_payout = numpy.mean([x['winning_payout'] for x in won_rounds])
print("Portfolio Status: Started With {} BNB - Ended with {} BNB".format(PORTFOLIO_INITIAL_AMOUNT,portfolio_total))
print("Played: {}, Won: {}, Lost: {} ".format(len(played_rounds),won,lost))
print("Success rate: {}%".format(round((won / len(played_rounds))* 100,2)))
print("Payout average: {}%".format(round(average_payout*100,2)))
print("Lost {} consecutive bets {} times".format(FAILURE_MAXIMUM,len(failure_log)))

# writing the data into the file
file = open(OUTPUT_CSV_FILE, 'w', newline='')
if len(played_rounds) > 0:
    fieldnames = list(played_rounds[0].keys())
    with file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(played_rounds)