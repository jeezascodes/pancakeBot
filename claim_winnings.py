import requests
from datetime import datetime
from datetime import timedelta
import time
import utils
from test_bot import claim_winnings
from utils import get_claimable_rounds


# Verify Parameters

while True:
    claimable_rounds = get_claimable_rounds()
    print(claimable_rounds)
    if len(claimable_rounds) > 1:
        for c_round in claimable_rounds:
            claim_winnings(int(c_round['round']['id']))
            time.sleep(20)
    elif len(claimable_rounds) == 1:
        c_round=claimable_rounds[0]
        claim_winnings(int(c_round['round']['id']))
       
    time.sleep(30)
