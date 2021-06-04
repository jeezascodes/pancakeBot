import requests


# A simple function to use requests.post to make the API call. Note the json= section.
def run_query(query):
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/pancakeswap/prediction', json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
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

# Duermo un minuto
result = run_query(graph_query.format(300, 0))
resutls_list = result['data']['rounds']
clean_list = list(filter(lambda x: x['closePrice'] != None, resutls_list))
clean_amounts = list(
    filter(lambda x: float(x['bullAmount']) > 0 and float(x['bearAmount']) > 0, clean_list))


def select_payout(block):
    bear = float(block['bearAmount'])
    bull = float(block['bullAmount'])

    if bull / bear < 0.3 or bear / bull < 0.3:
        return True
    else:
        return False


filtered_list = list(filter(select_payout, clean_amounts))


def get_accuracy():
    wrongs = 0
    for x in filtered_list:
        bear_amount = float(x['bearAmount'])
        bull_amount = float(x['bullAmount'])
        was_bear = bool(bear_amount > bull_amount)
        if was_bear and x['position'] == 'Bull':
            wrongs += 1
        elif not was_bear and x['position'] == 'Bear':
            wrongs += 1
        else:
            pass
    return len(filtered_list) / wrongs


print(get_accuracy())
print(len(filtered_list))
