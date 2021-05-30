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


users_query = """query{
  users( first: 1000, skip: 3000, orderBy: totalBets, orderDirection: desc, where: {totalBets_gt: 100}){
    id
    address
    createdAt
    updatedAt
    block
    totalBets
    totalBNB
    bets(first: 100)
    {
      position
      amount
      claimedAmount
    	round { position }
    }
  }
}"""

result = run_query(users_query)

winners = {}

users_list = result['data']['users']

for user in users_list:
    bets = user['bets']
    rights = list(filter(lambda x: x['position']
                         == x['round']['position'], bets))
    wrongs = list(filter(lambda x: x['position']
                         != x['round']['position'], bets))
    user_accuracy = len(wrongs) / len(rights)
    if user_accuracy < 0.25:
        winners[user['id']] = {'totalBets': user['totalBets'],
                               'totalBNB': user['totalBNB'], 'accuracy': user_accuracy}


print(winners)
