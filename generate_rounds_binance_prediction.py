import csv
from collections import OrderedDict
import numpy
from datetime import datetime
from datetime import timedelta
import requests
import time
from optparse import OptionParser



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
     end_timestamp_binance = (int(timestamp) * 1000)
     start_timestamp_binace = end_timestamp_binance - 3000

     endpoint = '/api/v3/aggTrades'
     query_string = {
        'symbol' : CURRENCY_SYMBOL,
        'startTime': start_timestamp_binace,
        'endTime': end_timestamp_binance,
        'limit' : 1
     }
     
     response = requests.get(BINANCE_API_URL+endpoint,params=query_string)
     data = response.json()[0]
     return data['p']
     


# Verify Parameters
parser = OptionParser()
parser.add_option("--begin_date", dest="min_date",
                  help="minimum date of a round lock to be considered, use '%Y-%m-%d' format")
parser.add_option("--end_date", dest="max_date",
                  help="maximum date of a round lock to be considered, use '%Y-%m-%d' format")
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the results of every round will be dumped",
                  default="binance_forecast_result.csv")
parser.add_option("--input_chainlink",
                  dest="input_chainlink",
                  help="csv file with chainlink prices",
                  default="chainlink_data.csv")
parser.add_option("--input_pancake",
                  dest="input_pancake",
                  help="csv file with pancake rounds",
                  default="pancake_data.csv")

(options, args) = parser.parse_args()

if not options.min_date or not options.max_date:
    parser.error(" --begin_date and --end_date are required")
    sys.exit(2)

try:
    min_date = datetime.strptime(options.min_date, '%Y-%m-%d')
    max_date = datetime.strptime(options.max_date, '%Y-%m-%d') + timedelta(1)
except:
    parser.error(" --begin_date and --end_date should be YYYY-MM-DD")
    sys.exit(2)



MIN_TIMESTAMP = datetime.timestamp(min_date)
MAX_TIMESTAMP = datetime.timestamp(max_date) 
CHAINLINK_ORIGIN_CSV_FILE = options.input_chainlink
PANCAKE_ORIGIN_CSV_FILE = options.input_pancake
RESULT_FILE = options.output_file
BINANCE_API_URL = 'https://api.binance.com'
CURRENCY_SYMBOL = 'BNBUSDT'




pancake_base_data = load_pancake_data_from_csv(PANCAKE_ORIGIN_CSV_FILE,MIN_TIMESTAMP,MAX_TIMESTAMP)
chainlink_dict = load_chainlink_timestamps_from_csv(CHAINLINK_ORIGIN_CSV_FILE,MIN_TIMESTAMP,MAX_TIMESTAMP)


for p_round in pancake_base_data:

    before_lock_timestamp = int(p_round['before_lock_window'])
    chainlink_timestamp = nearest_timestamp(chainlink_dict,before_lock_timestamp)
    if chainlink_timestamp > 0:
        chainlink_price =  chainlink_dict[chainlink_timestamp]
        binance_price = float(get_binance_price_for_timestamp(before_lock_timestamp))
        lock_price = float(p_round['lockPrice'])
        p_round['chainlink_price_age'] = before_lock_timestamp - int(chainlink_timestamp)
        p_round['chainlink_price'] = chainlink_price
        p_round['binance_price'] = binance_price
        p_round['binance_difference'] = abs(binance_price - lock_price)/lock_price
        p_round['binance_position'] = 'Bull' if binance_price > chainlink_price else 'Bear'
        time.sleep(0.1)
    else:
        p_round['chainlink_price_age'] = 'N/A'
        p_round['chainlink_price'] = 'N/A'
        p_round['binance_price'] = 'N/A'
        p_round['binance_difference'] = 'N/A'
        p_round['binance_position'] = 'N/A'
    print(p_round['lockAt'],"/",MAX_TIMESTAMP)

file = open(RESULT_FILE, 'w', newline='')
with file:
    writer = csv.DictWriter(file, fieldnames=list(pancake_base_data[0].keys()))
    writer.writeheader()
    writer.writerows(pancake_base_data)