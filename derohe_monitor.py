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
DISCORD_WEBHOOK = None
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
    parser.add_argument('--discord-webhook',
                        action='store',
                        help='Discord webhook url')
    parser.add_argument('--notify-count',
                        action='store',
                        help="Notify if you don't get reward after X minutes. defult disabled")
    return parser.parse_args()


def telegram(message):
    url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (
        TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
    _ = requests.get(url, timeout=10)


def discord(message):
    data = {'content': message}
    _ = requests.post(DISCORD_WEBHOOK, data, timeout=10)


def notify(message):
    if (TELEGRAM_BOT_TOKEN is not None
        and TELEGRAM_BOT_TOKEN != ""
        and TELEGRAM_CHAT_ID is not None
            and TELEGRAM_CHAT_ID != ""):
        telegram(message)
    if (DISCORD_WEBHOOK is not None
            and DISCORD_WEBHOOK != ""):
        discord(message)


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
    headers = {'Content-Type': 'application/json'}
    body = {"jsonrpc": "2.0",
            "id": "1",
            "method": method,
            "params": params}
    try:
        r = requests.post(rpc_server, json=body,
                          headers=headers, timeout=(9, 120))
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
        start_date += timedelta(minutes=1)
    max_height = 0
    for item in items:
        short_date = clean_date(item['time'])
        if short_date in amount_by_minute.keys():
            amount_by_minute[short_date] += item['amount']
    return amount_by_minute


def daily_totals(items, start_date):
    amount_by_day = dict()
    now = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    while start_date <= now:
        amount_by_day[start_date] = 0
        start_date += timedelta(days=1)
    while len(amount_by_day) > 7:
        amount_by_day.pop(min(amount_by_day))
    max_height = 0
    for item in items:
        short_date = clean_date(item['time']).replace(hour=0, minute=0, second=0, microsecond=0)
        if short_date in amount_by_day.keys():
            amount = item['amount']/RATIO
            if amount > 100:
                continue
            amount_by_day[short_date] += amount
    return amount_by_day


def populate_history():
    coinbase = get_transfers({'coinbase': True})
    last_7D = (datetime.today() - timedelta(days=7)
               ).replace(second=0, microsecond=0)
    last_24H = datetime.today() - timedelta(days=1)
    last_6H = datetime.today() - timedelta(hours=7)
    last_1H = datetime.today() - timedelta(hours=2)
    last_15M = datetime.today() - timedelta(minutes=15)
    gains = dict()
    gains['avg_15'] = deque(maxlen=15)
    gains['avg_60'] = deque(maxlen=60)
    gains['avg_360'] = deque(maxlen=360)
    gains['avg_1440'] = deque(maxlen=1440)
    gains['avg_10080'] = deque(maxlen=10080)
    short_hist = discretize_history(coinbase['result']['entries'], last_7D)
    for item in short_hist:
        amount = short_hist[item]/RATIO
        if amount > 100:
            continue
        if item > last_7D:
            gains['avg_10080'].append(amount)
        if item > last_24H:
            gains['avg_1440'].append(amount)
        if item > last_6H:
            gains['avg_360'].append(amount)
        if item > last_1H:
            gains['avg_60'].append(amount)
        if item > last_15M:
            gains['avg_15'].append(amount)
    return gains


def compute_chart():
    coinbase = get_transfers({'coinbase': True})
    last_7D = (datetime.today() - timedelta(days=7)
               ).replace(hour=0, minute=0, second=0, microsecond=0)
    days = daily_totals(coinbase['result']['entries'], last_7D)
    return days


def update_chart(days, diff):
    today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
    if today == max(days):
        days[today] += diff
    elif today > max(days):
        days.pop(min(days))
        days[today] = diff
    return days


def update(height):
    amounts = 0
    coinbase = get_transfers({'coinbase': True, 'min_height': height})
    if 'entries' in coinbase['result'].keys():
        items = coinbase['result']['entries']
        for item in items:
            if item['height'] <= height:
                break
            amount = item['amount']/RATIO
            if amount > 100:
                continue
            amounts += amount
    return amounts


def plot_graph(days):
    lines = ""
    max_value = max(days.values())
    count = 0
    for day in days:
        delimiter = "█" if count%2 == 0 else "░"
        lines += "| {:10}:{:51}{:12} |\n".format(day.strftime('%Y-%m-%d'), delimiter*(int(days[day]/max_value*50)), round(days[day],4))
        count += 1
    return lines



def run(rpc_server, max_zero):
    count_failure = 0
    passing_time = 0
    flag_notify = True
    diff = 0
    height = get_height()
    gains = populate_history()
    days = compute_chart()
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
        for item in gains:
            gains[item].append(diff)
        days = update_chart(days, diff)
        lines += "|{:^10}:{:^10}:{:^10}:{:^10}:{:^10}:{:^10}:{:^10}|\n".format(
            '', '1m', '15m', '1h', '6h', '24h', '7d')
        lines += "|{:^10}:{:^20}:{:^20}:{:^20}:{:^20}:{:^20}:{:^20}|\n".format('gain',
                                                                               print_sum(
                                                                                   [diff], 1),
                                                                               print_sum(
                                                                                   gains['avg_15'], 15),
                                                                               print_sum(
                                                                                   gains['avg_60'], 60),
                                                                               print_sum(
                                                                                   gains['avg_360'], 360),
                                                                               print_sum(
                                                                                   gains['avg_1440'], 1440),
                                                                               print_sum(
                                                                                   gains['avg_10080'], 10080))
        lines += "|"+" "*76+"|\n"
        if diff == 0:
            count_failure += 1
        else:
            count_failure = 0
            flag_notify = True
        lines += "| Current height:{0:59} |\n".format(current_height) 
        lines += "| Current amount:{0:59f} |\n".format(current_balance)
        now = datetime.now()
        fromatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        lines += "| Date:{0:>69} |\n".format(fromatted_date)
        lines += "------------------------------------------------------------------------------\n"
        lines += plot_graph(days)
        lines += "------------------------------------------------------------------------------\n"
        if max_zero > 0:
            if count_failure > max_zero:
                message = 'Since {} minutes you are not receiving rewards!'.format(
                    count_failure)
                lines += "\033[91m{}\033[00m\n".format(message)
                if flag_notify:
                    notify(message)
                    flag_notify = False
        if passing_time > 0: 
            for item in range(len(lines.split('\n'))-1):
                sys.stdout.write('\x1b[1A')
                sys.stdout.write('\x1b[2K')
        sys.stdout.write(lines)
        sys.stdout.flush()
        passing_time += 1
        time.sleep(60)
        


if __name__ == '__main__':
    max_zero = 0
    args = get_arguments()
    if args.rpc_server:
        rpc_server = "http://{}/json_rpc".format(args.rpc_server)
    if args.tg_bot:
        TELEGRAM_BOT_TOKEN = args.tg_bot
    if args.tg_chat:
        TELEGRAM_CHAT_ID = args.tg_chat
    if args.discord_webhook:
        DISCORD_WEBHOOK = args.discord_webhook
    if args.notify_count:
        max_zero = int(args.notify_count)
    run(rpc_server, max_zero)
