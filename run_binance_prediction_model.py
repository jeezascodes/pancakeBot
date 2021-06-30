import csv
from collections import OrderedDict
import numpy
from datetime import datetime
from datetime import timedelta
import requests
import time
from optparse import OptionParser
import utils
import pytz
import sys


def check_spearman(spearman_data, position_is_bear, spearman_min, price_diffence, spearman_aggressive, spearman_difference):

    if not spearman_difference is None and price_diffence > spearman_difference:
        return True
    
    if spearman_aggressive:
        return (
            (position_is_bear and spearman_data <= -1 * spearman_min) or
            (not position_is_bear and spearman_data >= spearman_min)
        )
    else:
        return (
            (position_is_bear and spearman_data < spearman_min) or
            (not position_is_bear and spearman_data > -1 * spearman_min)
        )


        

    
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
parser.add_option("--trauma_on",
                  dest="trauma_on",
                  action="store_true",
                  help="trauma")
parser.add_option("--apply_lost_penalty",
                  dest="apply_lost_penalty",
                  type="float",
                  help="add penalty to min_difference after a bet is lost"
                  )
parser.add_option("--spearman_min",
                  dest="spearman_min",
                  type="float",
                  help="minimum spearm coefficient to be accepted")
parser.add_option("--spearman_max_difference",
                  dest="spearman_max_difference",
                  type="float",
                  help="use conservative version of spearman")
parser.add_option("--spearman_aggressive",
                  dest="spearman_aggressive",
                  action="store_true",
                  help="use conservative version of spearman")
parser.add_option("--follow_public",
                  dest="follow_public",
                  action="store_true",
                  help="use public proxy to filtrate")                  
parser.add_option("--avoid_consecutive_from",
                  dest="avoid_consecutive_from",
                  type="int",
                  help="avoid X consecutibe bets")                  
parser.add_option("--consecutive_errors",
                  dest="consecutive_errors",
                  type="int",
                  help="consecutive error that should be logged",
                  default=2)
parser.add_option("--append_name",
                  dest="append_name",
                  type="string",
                  help="aditional column name for the information")
parser.add_option("--savings_from",
                  dest="savings_from",
                  type="float",
                  help="mounts above this will be saved")
parser.add_option("--restart_from",
                  dest="restart_from",
                  type="float",
                  help="every day starts at this value")




(options, args) = parser.parse_args()

MIN_TIMESTAMP, MAX_TIMESTAMP = utils.process_date_options(parser, options)
PORTFOLIO_PERCENTAGE = options.bet_percentage
PORTFOLIO_INITIAL_AMOUNT = options.wallet_initial
MAXIMUM_BET = options.bet_max_bnb
MAXIMUM_AGE = options.chainlink_age
FAILURE_MAXIMUM = options.consecutive_errors
ORIGIN_CSV_FILE = options.input_file
OUTPUT_CSV_FILE = options.output_file


SAVINGS_ENABLED = False
RESTART_ENABLED = False

if not options.savings_from is None:
    SAVINGS_ENABLED = True
SAVINGS_START = options.savings_from

if not options.restart_from is None:
    RESTART_ENABLED = True
RESTART_FROM = options.restart_from

if RESTART_ENABLED and SAVINGS_ENABLED:
    print("Both savings and restart cannot be activated at same time")
    sys.exit(2)

failure_log = []
played_rounds = []
round_data = load_data_from_csv(ORIGIN_CSV_FILE,MIN_TIMESTAMP,MAX_TIMESTAMP)
portfolio_total = PORTFOLIO_INITIAL_AMOUNT
consecutive_errors = []
portfolio_savings = 0
current_day = MIN_TIMESTAMP + 86400
failed_days = {}
savings_movements = []
day_resume = []
consecutive_bets = 0
won_bet = None
binance_difference = None
lost_bets = 0
last_difference = 0
last_2_defeats = []


for p_round in round_data:

    if int(p_round['lockAt']) > current_day:

        date = datetime.fromtimestamp(current_day) 
        if options.use_utc:
            date = datetime.fromtimestamp(current_day,pytz.utc)
    
        savings_object = {}
        savings_object['beginning_of_day_timestamp'] = date.strftime('%Y-%m-%d')
        if options.append_name:
            savings_object['type'] = options.append_name
        
        

        if RESTART_ENABLED:
            
            savings_object['value_at_beginning'] = portfolio_total
            portfolio_total = RESTART_FROM
    
        if SAVINGS_ENABLED:
        
            if portfolio_savings >= SAVINGS_START or portfolio_total >= SAVINGS_START:
                portfolio_savings += portfolio_total - SAVINGS_START
                savings_object['total'] = portfolio_savings
                savings_object['movement'] = portfolio_total - SAVINGS_START                
                portfolio_total = SAVINGS_START
        

        savings_movements.append(savings_object)            
        current_day += 86400
            

    if p_round['chainlink_price'] == 'N/A':
        continue
    
    #last_difference = 0 if binance_difference is None else binance_difference
    binance_difference = float(p_round['binance_difference'])
    chainlink_price_age = int(p_round['chainlink_price_age'])
    
    public_is_ok = True
    if options.follow_public:
        public_position = 'Bear' if float(p_round['lock_bear_amount']) >= float(p_round['lock_bull_amount']) else 'Bull'
        public_is_ok = public_position == p_round['binance_position']

    lost_last_bet = not won_bet is None and not won_bet
    
    difference_is_ok = binance_difference >= options.max_difference_percentage


    if lost_last_bet and not options.apply_lost_penalty is None and consecutive_bets > 0:
        difference_is_ok = binance_difference >= options.max_difference_percentage + (options.apply_lost_penalty*consecutive_bets) and binance_difference > last_difference

    if options.trauma_on:
        difference_is_ok = difference_is_ok and binance_difference >= options.max_difference_percentage + utils.lost_too_close_num(last_2_defeats,p_round['id'])
    
    
    if not options.min_difference_percentage is None :

        minimum = options.min_difference_percentage
        maximum = options.max_difference_percentage
        difference_is_ok = minimum <= binance_difference < maximum
    
    spearman_aggressive = options.spearman_aggressive
        

    spearman_is_ok = True
    if not options.spearman_min is None:
        round_spearman = float(p_round['spearman_coefficient'])
        bet_is_bear = p_round['binance_position'] == 'Bear'
        spearman_is_ok = check_spearman(
            round_spearman,
            bet_is_bear,
            options.spearman_min,
            binance_difference,
            spearman_aggressive,
            options.spearman_max_difference
        )

        
    age_is_ok = chainlink_price_age <= MAXIMUM_AGE

    
    
    if public_is_ok and difference_is_ok and spearman_is_ok and age_is_ok: 

        consecutive_bets += 1
        if not options.avoid_consecutive_from is None and consecutive_bets >= options.avoid_consecutive_from:
            continue
        
        
        if consecutive_bets > 1 and won_bet:
            bet_amount = (portfolio_total - bet_amount) * PORTFOLIO_PERCENTAGE
        else:
            bet_amount = portfolio_total * PORTFOLIO_PERCENTAGE
    

        if bet_amount > MAXIMUM_BET:
            bet_amount = MAXIMUM_BET

        if bet_amount < 0.001:
            if current_day in failed_days.keys():
                failed_days[current_day] += 1
            else:
                failed_days[current_day] = 1
            continue

        
        won_bet = p_round['binance_position'] == p_round['position']
        last_difference = binance_difference
        last_played_id = p_round['id']
        if not won_bet:
            lost_bets += 1
            last_2_defeats.append(last_played_id)
        else:
            lost_bets = 0
        bull = float(p_round['bullAmount']) + (bet_amount if p_round['binance_position'] == "Bull" else 0)
        bear = float(p_round['bearAmount']) + (bet_amount if p_round['binance_position'] == "Bear" else 0)
        if p_round['position'] == 'Bull':
            payout = bear/bull if bull > 0 else 0
        else:
            payout = bull/bear if bear > 0 else 0

        date = datetime.fromtimestamp(int(p_round['lockAt'])) 
        if options.use_utc:
            date = datetime.fromtimestamp(int(p_round['lockAt']),pytz.utc)
    
        
        bet_info = {
            'id': p_round['id'],
            'lock_date' : date.strftime('%Y-%m-%d %H:%M:%S'),
            'bet' : bet_amount,
            'status' : 'won' if won_bet else 'lost',
            'earnings' : payout * bet_amount if won_bet else -bet_amount,
            'winning_payout' : payout,
            'position_payout' : payout if won_bet else -1,
            'bet_position': p_round['binance_position'],
            'price_diffence': binance_difference,
        }

        if options.append_name:
            bet_info['type'] = options.append_name
        
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
    else:
        consecutive_bets = 0

won_rounds = list(filter(lambda x: x['status'] == 'won', played_rounds))
won = len(won_rounds)
lost = len(played_rounds) - won
average_payout = numpy.mean([x['winning_payout'] for x in won_rounds])
print("Portfolio Status: Started With {} BNB - Ended with {} BNB".format(PORTFOLIO_INITIAL_AMOUNT,portfolio_total+portfolio_savings))
print("Bets Portfolio size: {} BNB - Savings Size: {} BNB".format(portfolio_total, portfolio_savings))
print("Played: {}, Won: {}, Lost: {} ".format(len(played_rounds),won,lost))
print("Success rate: {}%".format(round((won / len(played_rounds))* 100,2)))
print("Payout average: {}%".format(round(average_payout*100,2)))
print("Lost {} consecutive bets {} times".format(FAILURE_MAXIMUM,len(failure_log)))
print("Couldn'bet on {} days".format(len(failed_days.keys())))

# writing the data into the file
file = open(OUTPUT_CSV_FILE, 'w', newline='')
if len(played_rounds) > 0:
    fieldnames = list(played_rounds[0].keys())
    with file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(played_rounds)

# # writing the data into the file
# savings_name = OUTPUT_CSV_FILE.lower().replace('.csv','')
# file = open(savings_name+'_savings.csv', 'w', newline='')
# if len(savings_movements) > 0:
#     fieldnames = list(savings_movements[0].keys())
#     with file:
#         writer = csv.DictWriter(file, fieldnames=fieldnames)
#         writer.writeheader()
#         writer.writerows(savings_movements)
