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
import sys



def nearest_timestamp(dict, value):

    nearest = numpy.searchsorted(list(dict.keys()),value,'right')
    if nearest == 0:
        print("En el diccionario no existe un timestamp menor o igual a",value)
        return -1
    else:
        return list(dict.keys())[nearest - 1]

    
def load_pancake_data_from_csv(file, min_t, max_t):
    result = []
    with open(file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if min_t <= int(row['lockAt']) < max_t:
                result.append(row)
    
    print("loaded {count} rounds inside interval from {file}".format(count=len(result), file=file))
    return result
    

def load_chainlink_timestamps_from_csv(file, min_t, max_t):
    
    result = {}
    with open(file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if min_t - 300 <= int(row['startedAt']) < max_t:
                result[int(row['startedAt'])] = int(row['price']) / (10**8)
        
    
    print("loaded {count} prices inside interval from {file}".format(count=len(result.keys()), file=file))
    result = OrderedDict(sorted(result.items()))
    return result


def get_binance_current_price():
    endpoint = '/api/v3/ticker/price'
    response = requests.get(BINANCE_API_URL+endpoint,params={'symbol': CURRENCY_SYMBOL})
    # FALTA VALIDAR PEO DEL WEIGHT Y LOS LIMITES
    data = response.json()
    return data['price']



# Verify Parameters
parser = OptionParser()
utils.add_date_options_to_parser(parser)
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the results of every round will be dumped",
                  default="binance_forecast_result.csv")
parser.add_option("--input_chainlink",
                  dest="input_chainlink",
                  help="csv file with chainlink prices",
                  default="chainlink_data.csv")
parser.add_option("--time_before_lock",
                  dest="time_before_lock",
                  help="time in seconds before teorical lock (300 seconds after start of block) when prices will be evaluated",
                  type="int",
                  default=10)
parser.add_option("--start_from_round",
                  dest="start_from_round",
                  help="start from a given round if the file has results already calculated",
                  type="int",
                  default=0)



(options, args) = parser.parse_args()

MIN_TIMESTAMP, MAX_TIMESTAMP = utils.process_date_options(parser, options)

CHAINLINK_ORIGIN_CSV_FILE = options.input_chainlink
RESULT_FILE = options.output_file
BINANCE_API_URL = 'https://api.binance.com'
CURRENCY_SYMBOL = 'BNBUSDT'
TIME_WINDOW = options.time_before_lock
FIELDS = ['id','position','startAt','startBlock','startHash','lockAt',
         'lockBlock','lockHash','lockPrice','endAt','endBlock','endHash',
         'closePrice','totalBets','totalAmount','bullBets','bullAmount',
         'bearBets','bearAmount','before_lock_window','chainlink_price_age',
         'chainlink_price','binance_price','binance_difference','binance_position']

# All these fields are calculated at the before_lock timestamp
EXTRA_FIELDS = [
    'spearman_coefficient', # Spearman for the timestamps and the prices of a minute of data
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

pancake_base_data = utils.get_rounds_from_pancake_using_range(MIN_TIMESTAMP,MAX_TIMESTAMP)
chainlink_dict = load_chainlink_timestamps_from_csv(CHAINLINK_ORIGIN_CSV_FILE,MIN_TIMESTAMP,MAX_TIMESTAMP)

append_write = 'a' if os.path.exists(RESULT_FILE) else 'w'
file = open(RESULT_FILE, append_write, newline='')
writer = csv.DictWriter(file, fieldnames=FIELDS)
if append_write == 'w':
    writer.writeheader()

i = 0
total_rounds = len(pancake_base_data)

for p_round in pancake_base_data:

    if not int(p_round['id']) < options.start_from_round:
        before_lock_timestamp = int(p_round['startAt']) + 300 - TIME_WINDOW
        chainlink_timestamp = nearest_timestamp(chainlink_dict,before_lock_timestamp)
        if chainlink_timestamp > 0:
            chainlink_price =  chainlink_dict[chainlink_timestamp]

            minute_data = utils.get_binance_minute_data_for_timestamp(before_lock_timestamp)
            minute_metrics = utils.calculate_metrics_for_array([float(elem['price']) for elem in minute_data])
            binance_price = minute_metrics['close']
            direction_data = utils.calculate_data_direction(minute_data)
            spearman, _  = direction_data['spearman']
            bets_result = utils.get_round_bets_at_timestamp(p_round['id'], before_lock_timestamp)
            
            p_round['chainlink_price_age'] = before_lock_timestamp - int(chainlink_timestamp)
            p_round['chainlink_price'] = chainlink_price
            p_round['binance_price'] = binance_price
            p_round['binance_difference'] = abs(binance_price - chainlink_price)/chainlink_price
            p_round['binance_position'] = 'Bull' if binance_price > chainlink_price else 'Bear'
            p_round['before_lock_window'] = before_lock_timestamp
            p_round['spearman_coefficient'] = spearman
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
            p_round['chainlink_price_age'] = 'N/A'
            p_round['chainlink_price'] = 'N/A'
            p_round['binance_price'] = 'N/A'
            p_round['binance_difference'] = 'N/A'
            p_round['binance_position'] = 'N/A'
            p_round['before_lock_window'] = 0
            p_round['spearman_coefficient'] = 'N/A'
            p_round['last_minute_average_difference'] = 'N/A'
            p_round['last_minute_median_difference'] = 'N/A'
            p_round['last_minute_average_position'] = 'N/A'
            p_round['last_minute_median_position'] = 'N/A'
            p_round['last_minute_min'] = 'N/A'
            p_round['last_minute_max'] = 'N/A'
            p_round['lock_bear_amount'] = 'N/A'
            p_round['lock_bear_bets'] = 'N/A'
            p_round['lock_bull_amount'] = 'N/A'
            p_round['lock_bull_bets'] = 'N/A'
            p_round['lock_total_amount'] = 'N/A'
            p_round['lock_total_bets'] = 'N/A'
    
        writer.writerow(p_round)
    
    i+=1
    if i % 10 == 0:
        print("processed: {} of {}".format(i, total_rounds))
