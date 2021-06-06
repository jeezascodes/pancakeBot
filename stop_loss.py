import requests
from datetime import datetime
from datetime import timedelta
import time
from utils import get_wallet_balance, get_if_user_has_open_bet


now = round(datetime.timestamp(datetime.now()), 0)

jesus = '0xf764B5925e530C5D5939C4d47CDCABB8F1D63bD0'


INITIAL_BALANCE = get_wallet_balance(jesus)
CURRENT_BALANCE = get_wallet_balance(jesus)
LOSS_LIMIT_PERCENTAGE = 0.7


current_hour = datetime.utcfromtimestamp(now).hour
current_minute = datetime.utcfromtimestamp(now).minute


while True:
    has_open_bet = get_if_user_has_open_bet()

    if current_hour == 0 and current_minute == 0:
        INITIAL_BALANCE = get_wallet_balance(jesus)

    CURRENT_BALANCE = get_wallet_balance(jesus)

    if not has_open_bet and CURRENT_BALANCE <= INITIAL_BALANCE * LOSS_LIMIT_PERCENTAGE:
        print('SHIT JUST HIT THE FAN BROU!')

    time.sleep(60)
