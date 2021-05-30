import requests
import json

# A simple function to use requests.post to make the API call. Note the json= section.


def run_query(query):
    request = requests.post(
        'https://api.thegraph.com/subgraphs/name/pancakeswap/prediction', json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(
            request.status_code, query))


users_query = """query{{
  user(id: "{}"){{
    id
    address
    createdAt
    updatedAt
    block
    totalBets
    totalBNB
    bets(first: 100, orderBy: createdAt, orderDirection: desc)
    {{
      position
      amount
      claimedAmount
    	round {{ position, id, bearAmount, bullAmount }}
    }}
  }}
}}"""

id_list = ['0x13b36e4fa197fbc5b1edf98a2d20f942fa1fab84',
           '0xa8a8ef181a5d700b33e7eb81a0b53ba05a2146ae', '0x8cd3bf70ff52eefcaf6c0834b6c9de4860550634']

rights = []


for user in id_list:
    result = run_query(users_query.format(user))
    bets_list = users_list = result['data']['user']['bets']
    # rights.append(list(filter(lambda x: x['position']
    #                           == x['round']['position'], bets_list)))
    rights.append(bets_list)

flat_list = [item for sublist in rights for item in sublist]

crossed_data = {}

for bet in flat_list:
    current_id = bet['round']['id']
    if current_id in crossed_data:
        crossed_data[current_id]['intersections'] = crossed_data[current_id]['intersections'] + 1
    else:
        bear = float(bet['round']['bearAmount'])
        bull = float(bet['round']['bullAmount'])
        format_data = {
            'position': bet['position'],
            'payout': [bear / bull if bet['position'] == 'Bull' else bull / bear],
            'intersections': 0
        }
        crossed_data[current_id] = format_data

list_of_dicts = [{k: v} for k, v in crossed_data.items()]


def get_total_intersections(block):
    block_id = [*block]
    if block[block_id[0]]['intersections'] > 0:
        return True
    else:
        False


filtered = list(filter(get_total_intersections, list_of_dicts))

for item in filtered:
    print(item)
print(len(filtered))
