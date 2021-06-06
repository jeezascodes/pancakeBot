import json

# Opening JSON file
with open('predictions_200.json') as json_file:
    data = json.load(json_file)

    results = data['data']['rounds']
    rights = 0
    wrongs = 0
    wrongs_list = []

    for x in range(0, len(results) - 1):

        close_price = results[x]['closePrice']
        close_price_last = results[x + 1]['closePrice']
        if bool(close_price) and bool(close_price_last):
            is_bear = bool(float(results[x]['bullAmount']) < float(
                results[x]['bearAmount']))
            if is_bear and float(close_price) > float(close_price_last):
                wrongs += 1
                wrongs_list.append('wrong')
            if is_bear and float(close_price) < float(close_price_last):
                rights += 1
                wrongs_list.append('right')
            if not is_bear and float(close_price) > float(close_price_last):
                rights += 1
                wrongs_list.append('right')
            if not is_bear and float(close_price) < float(close_price_last):
                wrongs += 1
                wrongs_list.append('wrong')

    # Print the data of dictionary
    print('rights', rights, 'wrongs', wrongs)
    print(rights/wrongs)
    print(wrongs_list)
