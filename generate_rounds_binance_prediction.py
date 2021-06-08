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

def get_binance_price_for_timestamp(timestamp):

     # Given a timestamp, we are going to look for the latest transaction
     # before the timestamp, binance require the timestamps with milliseconds
     # precission so we add three zeroes, one second before the timestamp should
     # be enough, i am using 3 seconds just for precaution
     end_timestamp_binance = int(timestamp) * 1000
     start_timestamp_binace = end_timestamp_binance - 5000

     endpoint = '/api/v3/aggTrades'
     query_string = {
        'symbol' : CURRENCY_SYMBOL,
        'startTime': start_timestamp_binace,
        'endTime': end_timestamp_binance,
        'limit' : 1
     }
     
     try: 
        response = requests.get(BINANCE_API_URL+endpoint,params=query_string)
        data = response.json()
        if len(data) > 0:
            return float(data[0]['p'])
        else:
            return -1
     except Exception as e:
         print(e)
         sys.exit(2)   


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
FIELDS = ['id','position','startAt','startBlock','startHash','lockAt','lockBlock','lockHash','lockPrice','endAt','endBlock','endHash','closePrice','totalBets','totalAmount','bullBets','bullAmount','bearBets','bearAmount','before_lock_window','chainlink_price_age','chainlink_price','binance_price','binance_difference','binance_position']

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
            binance_price = float(get_binance_price_for_timestamp(before_lock_timestamp))
            lock_price = float(p_round['lockPrice'])
            p_round['chainlink_price_age'] = before_lock_timestamp - int(chainlink_timestamp)
            p_round['chainlink_price'] = chainlink_price
            p_round['binance_price'] = binance_price
            p_round['binance_difference'] = abs(binance_price - chainlink_price)/chainlink_price
            p_round['binance_position'] = 'Bull' if binance_price > chainlink_price else 'Bear'
            p_round['before_lock_window'] = before_lock_timestamp
            time.sleep(0.1)
        else:
            p_round['chainlink_price_age'] = 'N/A'
            p_round['chainlink_price'] = 'N/A'
            p_round['binance_price'] = 'N/A'
            p_round['binance_difference'] = 'N/A'
            p_round['binance_position'] = 'N/A'
            p_rouud['before_lock_window'] = 0
    
        writer.writerow(p_round)
    
    i+=1
    if i % 10 == 0:
        print("processed: {} of {}".format(i, total_rounds))
