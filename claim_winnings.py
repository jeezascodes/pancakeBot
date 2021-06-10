import requests
from datetime import datetime
from datetime import timedelta
import time
import utils
from test_bot import claim_winnings,secure_winnigs
from utils import get_claimable_rounds


# Verify Parameters
# baseUnit = 1000000000000000000           
start_balance=100000000000000000
percentage_target=0.3
saving_wallet='0x0C4dFeAb618b3344d21070049b32CAAb80131577'

while True:
    claimable_rounds = get_claimable_rounds()
    if len(claimable_rounds) > 0:
        for c_round in claimable_rounds:
            claim_winnings(int(c_round['round']['id']))
    time.sleep(5)
    secure_winnigs(start_balance,percentage_target,saving_wallet)
