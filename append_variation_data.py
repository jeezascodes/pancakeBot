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
FIELDS = ['id','position','startAt','startBlock','startHash','lockAt','lockBlock','lockHash','lockPrice','endAt','endBlock','endHash','closePrice','totalBets','totalAmount','bullBets','bullAmount','bearBets','bearAmount','before_lock_window','chainlink_price_age','chainlink_price','binance_price','binance_difference','binance_position',"binance_price_stdev"]



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

        data = utils.get_binance_minute_data_for_timestamp(p_round['before_lock_window'])
        result = utils.calculate_metrics_for_array([float(elem['price']) for elem in data])
        if float(result['mean']) > 0:
            p_round['binance_price_stdev'] = float(result['stdev'])/float(result['mean'])
        else:
            p_round['binance_price_stdev'] = 0
        
        writer.writerow(p_round)
        time.sleep(0.1)
    
    i+=1
    if i % 10 == 0:
        print("processed: {} of {}".format(i, total_rounds))
