from web3 import Web3
import csv
from datetime import datetime
from datetime import timedelta
from optparse import OptionParser
from constants import chainlink_addres, chainlink_abi
import utils
import time
import os


parser = OptionParser()
utils.add_date_options_to_parser(parser)
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the prices will be dumped",
                  default="minute_data_to.csv")
parser.add_option("--start_from_timestamp",
                  dest="start_from_timestamp",
                  help="start from a given round if the file has results already calculated",
                  type="int",
                  default=0)


(options, args) = parser.parse_args()

FIELDS = ['timestamp', 'min', 'max', 'mean', 'stdev', 'price_variation', 'open', 'close']
MIN_TIMESTAMP, MAX_TIMESTAMP = utils.process_date_options(parser, options)
FILE = options.output_file


append_write = 'a' if os.path.exists(FILE) else 'w'
file = open(FILE, append_write, newline='')
writer = csv.DictWriter(file, fieldnames=FIELDS)
if append_write == 'w':
    writer.writeheader()

total_minutes = (MAX_TIMESTAMP - MIN_TIMESTAMP) / 60
current_minute = MIN_TIMESTAMP + 60
counter = 0
while current_minute < MAX_TIMESTAMP:

    if current_minute > options.start_from_timestamp:
        data = utils.get_binance_minute_data_for_timestamp(current_minute)
        result = utils.calculate_metrics_for_array([float(elem['price']) for elem in data])
        result['timestamp'] = current_minute
        if result['mean'] != 0:
            writer.writerow(result)
        time.sleep(0.1)
    
    counter += 1
    current_minute += 60
    
    if counter % 10 == 0:
        print("processed: {} of {}".format(counter, total_minutes))

