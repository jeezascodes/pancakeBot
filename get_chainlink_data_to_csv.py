from web3 import Web3
import csv
from datetime import datetime
from datetime import timedelta
from optparse import OptionParser

def get_chainlink_data_using_interval(min_t, max_t, seed=None, average=90):
    web3 = Web3(Web3.HTTPProvider('https://bsc-dataseed1.ninicoin.io/'))
    abi = (
            '[{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},'
            '{"inputs":[],"name":"description","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},'
            '{"inputs":[{"internalType":"uint80","name":"_roundId","type":"uint80"}],"name":"getRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},'
            '{"inputs":[{"internalType":"uint80","name":"_id","type":"uint80"}],"name":"getPreviousAnswer","outputs":[{"internalType":"int256","name":"price","type":"int256"}],"stateMutability":"view","type":"function"},'
            '{"inputs":[],"name":"latestRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},'
            '{"inputs":[],"name":"version","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
            )
    addr = '0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE'
    contract = web3.eth.contract(address=addr, abi=abi)
    

    if seed is None:
        data = contract.functions.latestRoundData().call()
    else:
        data = contract.functions.getRoundData(seed).call()

    # Estimate an aproximation of the first roundid given the timestamp
    # and the id obtained from the seed_id
    initial_id_guess = int(data[0]) - int(round((data[2]-min_t)/average,0))

    result = []
    keep_looking=True
    exception_count=0
    while keep_looking and exception_count < 5:
        try:
            print(initial_id_guess)
            data = contract.functions.getRoundData(initial_id_guess).call()
            if data[2] <= min_t:
                keep_looking = False
            else:
                initial_id_guess -= 1
            exception_count = 0
        except Exception as e:
            print("Something went wrong",e)
            initial_id_guess -= 1
            exception_count += 1


    keep_looking=True
    exception_count=0
    while keep_looking and exception_count < 5:
        try:
            data = contract.functions.getRoundData(initial_id_guess).call()
            if min_t - 300 <= int(data[2]) < max_t:
                result.append(data)
            elif int(data[2]) > max_t:
                keep_looking = False
            exception_count = 0
            print("{} / {}".format(data[2], max_t))
        except:
            print("Something went wrong")
            exception_count += 1

        initial_id_guess += 1

    return result



def get_chainlink_data_using_count(count=4500):

    web3 = Web3(Web3.HTTPProvider(
        'https://bsc-dataseed.binance.org/'))
    abi = '[{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"description","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint80","name":"_roundId","type":"uint80"}],"name":"getRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"latestRoundData","outputs":[{"internalType":"uint80","name":"roundId","type":"uint80"},{"internalType":"int256","name":"answer","type":"int256"},{"internalType":"uint256","name":"startedAt","type":"uint256"},{"internalType":"uint256","name":"updatedAt","type":"uint256"},{"internalType":"uint80","name":"answeredInRound","type":"uint80"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"version","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}]'
    addr = '0x0567F2323251f0Aab15c8dFb1967E4e8A7D42aeE'
    contract = web3.eth.contract(address=addr, abi=abi)
    latestData = contract.functions.latestRoundData().call()

    collected_data = []
    for x in reversed(range(latestData[0] - count, latestData[0])):
        try:
            roundData = contract.functions.getRoundData(x).call()
            collected_data.append(roundData)
        except:
            print("An exception occurred")

parser = OptionParser()
parser.add_option("--begin_date", dest="min_date",
                  help="minimum date of a round lock to be considered, use '%Y-%m-%d' format")
parser.add_option("--end_date", dest="max_date",
                  help="maximum date of a round lock to be considered, use '%Y-%m-%d' format")
parser.add_option("--output_file",
                  dest="output_file",
                  help="csv where the prices will be dumped",
                  default="chainlink_data.csv")

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
FILE = options.output_file

#collected_data = get_chainlink_data_using_count(4500)
collected_data = get_chainlink_data_using_interval(MIN_TIMESTAMP,MAX_TIMESTAMP)

file = open(FILE, 'w', newline='')

# writing the data into the file
with file:
    write = csv.writer(file)
    write.writerow(['roundId','price','startedAt','updatedAt','answeredInRound'])
    write.writerows(collected_data)