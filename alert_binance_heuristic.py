import requests
from datetime import datetime
from datetime import timedelta
import pprint
import time
import tkinter
from tkinter import *
import utils
from optparse import OptionParser




# Verify Parameters
parser = OptionParser()
parser.add_option("--time_window",
                  dest="time_window",
                  type="int",
                  default=15,
                  help="seconds before lock when live round will be checked and window will be showed")
parser.add_option("--round_duration",
                  dest="round_duration",
                  type="int",
                  default=308,
                  help="estimated seconds for a round to close since its lock time")
parser.add_option("--difference_percentage",
                  dest="difference_percentage",
                  type="float",
                  help="minimal difference between binance and chainlink to enter in a bet",
                  default=0.00350240113364098)
parser.add_option("--chainlink_age",
                  dest="chainlink_age",
                  type="int",
                  help="maximal age (seconds) for a chainlink price to enter in a bet",
                  default=70)


(options, args) = parser.parse_args()

TIME_WINDOW = options.time_window
ROUND_DURATION = options.round_duration # Average from 28/05/2021 to 31/05/2021
CHAINLINK_MAXIMUM_AGE = options.chainlink_age
PRICE_MINIMUM_DIFFERENCE = options.difference_percentage

current_active_round_id = None
round_processed = False

root = Tk()
root.geometry("600x200")
t = Label(root, text = 'A title', font = "50") 
t.pack()
m = Label(root, text = 'Some message', font="30")
m.pack()

while True:
  
  if current_active_round_id is None or round_processed:
    result = utils.get_pancake_last_rounds(2,0)
    live_round = result[1]

  now = round(datetime.timestamp(datetime.now()),0)
  starts_at = int(live_round['lockAt'])
  should_close_at = starts_at + ROUND_DURATION
  should_wake_up_at = should_close_at - TIME_WINDOW

  if now >= should_close_at:
    print("El bloque {} esta en proceso de cierre".format(live_round['id']))
    time.sleep(1)
    continue
    
  # Si el bloque es nuevo vemos por cuanto tiempo dormir
  if current_active_round_id != live_round['id']:
    print("Nuevo bloque 'live' {}".format(live_round['id']))
    current_active_round_id = live_round['id']    
    if now <= should_wake_up_at:
      seconds_left = should_wake_up_at - now
      print("Faltan {} segundos para revisar el bloque {}".format(seconds_left, live_round['id']))
      round_processed = False
      time.sleep(seconds_left)
      continue
    elif now >= should_wake_up_at + 5: 
      seconds_left = should_close_at - now
      print("Detectamos el bloque {} muy tarde, esperare {} segundos por el proximo".format(live_round['id'],seconds_left))
      round_processed = True
      time.sleep(seconds_left if seconds_left >= 0 else 1)
      continue
    else:
      print("Detectamos el bloque {} justo a tiempo, procederemos a revisarlo",format(live_round['id']))
  

  chainlink_price = utils.get_chainlink_last_round_price()
  if chainlink_price['age'] < CHAINLINK_MAXIMUM_AGE:

    print("Se cumple la edad")
    binance_price = utils.get_binance_last_price()
    base_price_difference = abs(binance_price - chainlink_price['price'])/chainlink_price['price']

    if base_price_difference >= PRICE_MINIMUM_DIFFERENCE:
      
      print("Se cumple la diferencia")
      last_price_difference = base_price_difference
      current_price_difference = base_price_difference
      trend_string = ""
      while now < should_close_at:

        if current_price_difference >= PRICE_MINIMUM_DIFFERENCE:
          position = 'Bull' if binance_price > chainlink_price['price'] else 'Bear'
          title = "Apostar a {}".format(position)
          message_1 = "El precio actual en Binance es {}".format(binance_price)
          message_2 = "\nTrend : {}"
          message_3 = "\n\n{} segundos aprox. para cerrar el bloque".format(should_close_at - now)
          if current_price_difference < last_price_difference:
            trend_string += '↓'
          elif current_price_difference > last_price_difference:
            trend_string += '↑'
          else:
            trend_string += "-"
          last_price_difference = current_price_difference
          message = message_1 + message_2.format(trend_string[-10:]) + message_3
        else:
          title = "NO APUESTES!!"
          message = "La diferencia entre precios bajo demasiado\nEl precio actual en Binance es{}".format(binance_price)

        t.configure(text=title)
        m.configure(text=message)
        root.update()
        root.deiconify()

        time.sleep(0.5)
        now = round(datetime.timestamp(datetime.now()),0)
        binance_price = utils.get_binance_last_price()
        current_price_difference = abs(binance_price - chainlink_price['price'])/chainlink_price['price']

      print("Se destruira la ventana")
      root.withdraw()
      round_processed = True
    else:
      seconds_left = should_close_at - now
      print("La diferencia de precios es muy baja, esperare {} segundos por el proximo".format(seconds_left))
      round_processed = True
      time.sleep(seconds_left if seconds_left > 0 else 5)      
  else:
    seconds_left = should_close_at - now 
    print("La edad del precio es muy alta, esperare {} segundos por el proximo".format(seconds_left))
    round_processed = True
    time.sleep(seconds_left if seconds_left > 0 else 5)
