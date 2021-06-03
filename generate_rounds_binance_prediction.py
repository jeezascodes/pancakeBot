import csv
from collections import OrderedDict
import numpy
from datetime import datetime
from datetime import timedelta
import requests
import time


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
     



MIN_TIMESTAMP = 1622178000
#MAX_TIMESTAMP = 1622178000 + 600
MAX_TIMESTAMP = 1622523600
CHAINLINK_ORIGIN_CSV_FILE = 'chainlink_data.csv'
PANCAKE_ORIGIN_CSV_FILE = 'pancake_data.csv'
RESULT_FILE = 'binance_forecast_result.csv'
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