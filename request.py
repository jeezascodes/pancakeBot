import requests
from datetime import datetime
from datetime import timedelta
import pprint
import time
import tkinter
from tkinter import *


def round_is_wrong(bet_round):

    bear_amount = float(bet_round['bearAmount'])
    bull_amount = float(bet_round['bullAmount'])
    locked_price = float(bet_round['lockPrice'])
    closed_price = float(bet_round['closePrice'])

    people_bet = ''

    if bear_amount > bull_amount:
        people_bet = 'Bear'
    elif bull_amount > bear_amount:
        people_bet = 'Bull'
    else:
        people_bet = 'Tied'

    if closed_price == locked_price:
        print("Se jodio todo el mundo")
        return false

    people_was_wrong = people_bet != bet_round['position']

    if people_was_wrong and bear_amount + bull_amount < MINIMUM_POOL_SIZE:
        print("La gente se equivoco, pero el pool es muy pequeño {}".format(
            bear_amount + bull_amount))
    elif people_was_wrong:
        print("La gente se equivo, activo")

    return people_was_wrong and bear_amount + bull_amount > MINIMUM_POOL_SIZE


# A simple function to use requests.post to make the API call. Note the json= section.
def run_query(query):
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/pancakeswap/prediction', json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
        print(request.headers)
        raise Exception("Query failed to run by returning code of {}. {}".format(
            request.status_code, query))


graph_query = """
query getMarketData {{
        rounds(first: {}, skip: {}, orderBy: epoch, orderDirection: desc) {{

  id
  epoch
  failed
  startAt
  startBlock
  lockAt
  lockBlock
  lockPrice
  endAt
  endBlock
  closePrice
  totalBets
  totalAmount
  bullBets
  bullAmount
  bearBets
  bearAmount
  position

        }}
        market(id: 1) {{
          id
          paused
          epoch {{ epoch }}
        }}
      }}
"""


MINIMUM_POOL_SIZE = 20

current_closed_id = None
while True:

    # Duermo un minuto
    result = run_query(graph_query.format(3, 0))
    new_closed = result['data']['rounds'][-1]
    if current_closed_id is None or current_closed_id != new_closed['id']:
        print("Bloque cerrado nuevo {}".format(new_closed['id']))
        current_closed_id = new_closed['id']
        now = datetime.now()
        current_active_round = result['data']['rounds'][1]
        starts_at = datetime.fromtimestamp(int(current_active_round['lockAt']))
        should_close_at = starts_at + timedelta(0, 300)
        seconds_left = (should_close_at - now).total_seconds()
        # if round_is_wrong(new_closed):
        if True:
            print("Hay que abrir una ventana")
            root = Tk()
            root.geometry("300x200")
            t = Label(root, text='A title', font="50")
            t.pack()
            m = Label(root, text='Some message', font="30")
            m.pack()
            next_round = result['data']['rounds'][0]
            now = datetime.now()
            watched_round_id = next_round['id']
            new_round_id = next_round['id']
            starts_at = datetime.fromtimestamp(int(next_round['startAt']))
            should_lock_at = starts_at + timedelta(0, 300)
            seconds_left = (should_lock_at - now).total_seconds()
            while seconds_left > 0 and watched_round_id == new_round_id:

                next_round = run_query(graph_query.format(1, 0))[
                    'data']['rounds'][0]
                new_round_id = next_round['id']
                now = datetime.now()
                starts_at = datetime.fromtimestamp(int(next_round['startAt']))
                should_lock_at = starts_at + timedelta(0, 300)
                seconds_left = (should_lock_at - now).total_seconds()
                bull_amount = float(next_round['bullAmount'])
                bear_amount = float(next_round['bearAmount'])

                bull_stats = {
                    'amount': bull_amount,
                    'count': next_round['bullBets'],
                    'payout': 0 if bull_amount == 0 else round((bear_amount/bull_amount) + 1, 2)
                }
                bear_stats = {
                    'amount': bear_amount,
                    'count': next_round['bearBets'],
                    'payout': 0 if bear_amount == 0 else round((bull_amount/bear_amount) + 1, 2)
                }

                title = 'time left: {}'.format(round(seconds_left, 0))
                message = '''
          most people is betting {}!
          bull payout: {}
          bear payout: {}
        
        '''.format(
                    'bull' if bull_stats['amount'] > bear_stats['amount'] else 'bear',
                    bull_stats['payout'],
                    bear_stats['payout']

                )

                t.configure(text=title)
                m.configure(text=message)
                root.update()
                if seconds_left > 60:
                    time.sleep(10)
                else:
                    time.sleep(0.5)
            root.destroy()

        else:
            print("El bloque estuvo bien teoricamente, a mimir por {} seg".format(
                seconds_left))
            time.sleep(60 if seconds_left < 0 else seconds_left)
