import csv
from collections import OrderedDict
import numpy
from datetime import datetime
from datetime import timedelta
import requests
import time
from optparse import OptionParser
import utils
import os

    
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
                  default="binance_forecast_result_with_stdev.csv")
parser.add_option("--input_file",
                  dest="input_file",
                  help="csv file with the rounds information",
                  default="binance_forecast_result.csv")
parser.add_option("--start_from_round",
                  dest="start_from_round",
                  help="start from a given round if the file has results already calculated",
                  type="int",
                  default=0)


(options, args) = parser.parse_args()

MIN_TIMESTAMP, MAX_TIMESTAMP = utils.process_date_options(parser, options)
ORIGIN_CSV_FILE = options.input_file
OUTPUT_CSV_FILE = options.output_file
FIELDS = ['id','position','startAt','startBlock','startHash','lockAt',
    'lockBlock','lockHash','lockPrice','endAt','endBlock','endHash',
    'closePrice','totalBets','totalAmount','bullBets','bullAmount',
    'bearBets','bearAmount','before_lock_window','chainlink_price_age',
    'chainlink_price','binance_price','binance_difference','binance_position']

# All these fields are calculated at the before_lock timestamp
EXTRA_FIELDS = [
    'binance_price_stdev', # Relation between the average price of a minute and it standard deviation
    'spearman_coefficient', # Spearman for the timestamps and the prices of a minute of data
    'spearman_p_value', # Spearman p_value for the data above
    'last_minute_average_difference', # Average of the last minute divided between the chainlink price
    'last_minute_median_difference', # Median of the last minute divided between the chainlink price
    'last_minute_average_position', # Position according to average
    'last_minute_median_position', # Position according to median
    'last_minute_min',
    'last_minute_max',
    'last_minute_average_difference', # Average of the last minute divided between the chainlink price
    'last_minute_median_difference', # Median of the last minute divided between the chainlink price
    'lock_bear_amount', # Bear amount of the round at before_lock timestamp
    'lock_bear_bets',
    'lock_bull_amount',
    'lock_bull_bets',
    'lock_total_bets',
    'lock_total_amount'
]

FIELDS += EXTRA_FIELDS


round_data = load_data_from_csv(ORIGIN_CSV_FILE,MIN_TIMESTAMP,MAX_TIMESTAMP)
append_write = 'a' if os.path.exists(OUTPUT_CSV_FILE) else 'w'
file = open(OUTPUT_CSV_FILE, append_write, newline='')
writer = csv.DictWriter(file, fieldnames=FIELDS)
if append_write == 'w':
    writer.writeheader()

i = 0
total_rounds = len(round_data)



for p_round in round_data:

    if int(p_round['id']) > options.start_from_round:

        minute_data = utils.get_binance_minute_data_for_timestamp(p_round['before_lock_window'])
        minute_metrics = utils.calculate_metrics_for_array([float(elem['price']) for elem in minute_data])

        bets_result = utils.get_round_bets_at_timestamp(p_round['id'], p_round['before_lock_window'])
        if minute_metrics['mean'] > 0:
            spearman, p_value = utils.calculate_data_direction(minute_data)
            chainlink_price = float(p_round['chainlink_price'])
            
            p_round['spearman_coefficient'] = spearman
            p_round['spearman_p_value'] = p_value
            p_round['binance_price_stdev'] = minute_metrics['stdev']/minute_metrics['mean']
            p_round['last_minute_average_difference'] = abs(minute_metrics['mean'] - chainlink_price)/chainlink_price
            p_round['last_minute_median_difference'] = abs(minute_metrics['median'] - chainlink_price)/chainlink_price
            p_round['last_minute_average_position'] = 'Bull' if minute_metrics['mean'] > chainlink_price else 'Bear'
            p_round['last_minute_median_position'] = 'Bull' if minute_metrics['median'] > chainlink_price else 'Bear'
            p_round['last_minute_min'] = minute_metrics['min']
            p_round['last_minute_max'] = minute_metrics['max']
            p_round['lock_bear_amount'] = bets_result['bearAmount']
            p_round['lock_bear_bets'] = bets_result['bearBets']
            p_round['lock_bull_amount'] = bets_result['bullAmount']
            p_round['lock_bull_bets'] = bets_result['bullBets']
            p_round['lock_total_amount'] = bets_result['totalAmount']
            p_round['lock_total_bets'] = bets_result['totalBets']

        else:
            p_round['spearman_coefficient'] = -1
            p_round['spearman_p_value'] = -1
            p_round['binance_price_stdev'] = 0
            p_round['last_minute_average_difference'] = 0
            p_round['last_minute_median_difference'] = 0
            p_round['lock_bear_amount'] = 0
            p_round['lock_bear_bets'] = 0
            p_round['lock_bull_amount'] = 0
            p_round['lock_bull_bets'] = 0
            p_round['lock_total_amount'] = 0
            p_round['lock_total_bets'] = 0

        
        writer.writerow(p_round)

    i+=1
    if i % 10 == 0:
        print("processed: {} of {}".format(i, total_rounds))
