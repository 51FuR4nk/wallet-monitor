#!/usr/bin/env python3
'''
This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License
as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program.
If not, see <https://www.gnu.org/licenses/>. 
'''

#import curses
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from dateutil import parser
import argparse
from collections import deque


RATIO = 100000
TELEGRAM_BOT_TOKEN = None
TELEGRAM_CHAT_ID = None
rpc_server = "http://127.0.0.1:10103/json_rpc"
HEIGHT = 0

def get_arguments():
    """
    parse the argument provided to the script
    """
    parser = argparse.ArgumentParser(
        description='DeroHE wallet monitor',
        epilog='Created by 51|Fu.R4nk',
        usage='python3 %s [-a]')
    parser.add_argument('--rpc-server',
                        action='store',
                        help='rpc-server address. Default 127.0.0.1:10109')
    parser.add_argument('--tg-bot',
                        action='store',
                        help='Telegram bot token')
    parser.add_argument('--tg-chat',
                        action='store',
                        help='Telegram chat id')
    parser.add_argument('--notify-count',
                        action='store',
                        help="Notify if you don't get reward after X minutes. defult disabled")
    return parser.parse_args()

def telegram(message):
   url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (
       TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
   _ = requests.get(url, timeout=10)

def notify(message):
    if (TELEGRAM_BOT_TOKEN is not None and
       TELEGRAM_BOT_TOKEN != "" and
       TELEGRAM_CHAT_ID is not None and
       TELEGRAM_CHAT_ID != ""):
        telegram(message)


def print_avg(data, supposed_len):
   if supposed_len == 1:
      return "\033[96m{}\033[00m".format(round(sum(data)/supposed_len, 4))
   if len(data) == supposed_len:
      return "\033[92m{}\033[00m".format(round(sum(data)/supposed_len, 4))
   return "\033[93m{}\033[00m".format(round(sum(data)/supposed_len, 4))


def print_sum(data, supposed_len):
   if supposed_len == 1:
      return "\033[96m{}\033[00m".format(round(sum(data), 4))
   if len(data) == supposed_len:
      return "\033[92m{}\033[00m".format(round(sum(data), 4))
   return "\033[93m{}\033[00m".format(round(sum(data), 4))


def generic_call(method, params=None):
   headers = {'Content-Type': 'application/json' }
   body = { "jsonrpc": "2.0",
            "id": "1",
            "method": method,
            "params": params}
   try:
      r = requests.post(rpc_server, json=body, headers=headers, timeout=(9, 120))
   except:
      print("RPC not found. Terminating")
      sys.exit()
   return r


def get_balance():
   result = generic_call("GetBalance")
   return json.loads(result.text)['result']['balance']/RATIO


def get_height():
   result = generic_call("GetHeight")
   return json.loads(result.text)['result']['height']


def get_transfers(param=None):
   result = generic_call("GetTransfers", param)
   return json.loads(result.text)


def clean_date(date):
   return parser.parse(date, ignoretz=True).replace(second=0, microsecond=0)

def discretize_history(items, start_date):
   amount_by_minute = dict()
   now = datetime.today().replace(second=0, microsecond=0)
   while start_date <= now:
      amount_by_minute[start_date] = 0
      start_date += timedelta(minutes = 1)
   max_height = 0
   for item in items:
      short_date = clean_date(item['time'])
      if short_date in amount_by_minute.keys():
         amount_by_minute[short_date] += item['amount']
   return amount_by_minute


def populate_history():
   coinbase = get_transfers({'coinbase':True})
   last_7D = (datetime.today() - timedelta(days = 7 )).replace(second=0, microsecond=0)
   last_24H = datetime.today() - timedelta(days = 1 )
   last_6H = datetime.today() - timedelta(hours = 7 )
   last_1H = datetime.today() - timedelta(hours = 2 )
   last_15M = datetime.today() - timedelta(minutes = 15 )
   avg_15 = deque(maxlen=15)
   avg_60 = deque(maxlen=60)
   avg_360 = deque(maxlen=360)
   avg_1440 = deque(maxlen=1440)
   avg_10080 = deque(maxlen=10080)
   #total = 0
   short_hist = discretize_history(coinbase['result']['entries'], last_7D)
   for item in short_hist:
      amount = short_hist[item]/RATIO
      if amount > 100:
         continue
      #total += amount
      if item > last_7D:
         avg_10080.append(amount)
      if item > last_24H:
         avg_1440.append(amount)
      if item > last_6H:
         avg_360.append(amount)
      if item > last_1H:
         avg_60.append(amount)
      if item > last_15M:
         avg_15.append(amount)
   return avg_15, avg_60, avg_360, avg_1440, avg_10080#, total


def update(height):
   amounts = 0
   coinbase = get_transfers({'coinbase':True})
   items = coinbase['result']['entries']
   for index in range(1,len(coinbase['result']['entries'])):
      if items[-index]['height'] <= height:
         break
      amount = items[-index]['amount']/RATIO
      if amount > 100:
         continue
      amounts += amount
   return amounts



def run(rpc_server, max_zero):
   prev_balance = 0
   count_failure = 0
   passing_time = 0
   flag_notify = True
   diff = 0
   height = get_height()
   avg_15, avg_60, avg_360, avg_1440, avg_10080 = populate_history()
   while True:
      lines = ""
      sys.stdout.write("\r")
      current_balance = get_balance()
      lines += "------------------------------------------------------------------------------\n"
      current_height = get_height()
      if current_height > height:
         diff = update(height)
         height = current_height
      else:
         diff = 0
      avg_15.append(diff)
      avg_60.append(diff)
      avg_360.append(diff)
      avg_1440.append(diff)
      avg_10080.append(diff)
      #total += diff
      lines += "|{:^10}:{:^10}:{:^10}:{:^10}:{:^10}:{:^10}:{:^10}|\n".format('','1m','15m','1h','6h','24h','7d')
      lines += "|{:^10}:{:^20}:{:^20}:{:^20}:{:^20}:{:^20}:{:^20}|\n".format('gain',
                                                                             print_sum([diff], 1),
                                                                             print_sum(avg_15, 15),
                                                                             print_sum(avg_60, 60),
                                                                             print_sum(avg_360, 360),
                                                                             print_sum(avg_1440, 1440),
                                                                             print_sum(avg_10080, 10080))
                                                                             #print_sum([total], 1))
      lines += "|"+" "*76+"|\n"
      if diff == 0:
         count_failure += 1
      else:
         count_failure = 0
         flag_notify = True
      lines += "| Current amount:{0:59f} |\n".format(current_balance)
      now = datetime.now()
      fromatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
      lines += "| Date:{0:>69} |\n".format(fromatted_date)
      if passing_time % 15 == 0:
         print
      lines += "------------------------------------------------------------------------------\n"
      if max_zero > 0:
         if count_failure > max_zero:
            message = 'Since {} minutes you are not receiving rewards!'.format(count_failure)
            lines += "\033[91m{}\033[00m\n".format(message)
            if flag_notify:
               notify(message)
               flag_notify=False
      prev_balance = current_balance
      passing_time += 1
      sys.stdout.write(lines)
      sys.stdout.flush()
      time.sleep(60)
      for item in range(len(lines.split('\n'))-1):
         sys.stdout.write('\x1b[1A')
         sys.stdout.write('\x1b[2K')

                                                               
if __name__ == '__main__':
   max_zero = 0
   args = get_arguments()
   if args.rpc_server:
      rpc_server = "http://{}/json_rpc".format(args.rpc_server)
   if args.tg_bot:
      TELEGRAM_BOT_TOKEN = args.tg_bot
   if args.tg_chat:
      TELEGRAM_CHAT_ID = args.tg_chat
   if args.notify_count:
      max_zero = int(args.notify_count)
   run(rpc_server, max_zero)
