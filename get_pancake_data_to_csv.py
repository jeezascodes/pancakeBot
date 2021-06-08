from web3 import Web3
import csv
import utils
import copy
from datetime import timedelta
from datetime import datetime
import pytz
from optparse import OptionParser


    



parser = OptionParser()
utils.add_date_options_to_parser(parser)
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the prices will be dumped",
                  default="pancake_data.csv")

(options, args) = parser.parse_args()


MIN_TIMESTAMP, MAX_TIMESTAMP = utils.process_date_options(parser,options)
FILE = options.output_file

collected_data = utils.get_rounds_from_pancake_using_range(MIN_TIMESTAMP,MAX_TIMESTAMP)
file = open(FILE, 'w', newline='')
# writing the data into the file

if len(collected_data) > 0:

    with file:
        writer = csv.DictWriter(file, fieldnames=list(collected_data[0].keys()))
        writer.writeheader()
        writer.writerows(collected_data)