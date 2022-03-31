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
wallet_rpc_server = "http://127.0.0.1:10103/json_rpc"
node_rpc_server = "http://127.0.0.1:10103/json_rpc"
HEIGHT = 0
DAYS = 7


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
                        help='Wallet rpc-server address. Default 127.0.0.1:10103')
    parser.add_argument('--node-rpc-server',
                        action='store',
                        help='Node wallet rpc-server address.')
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
    parser.add_argument('--one-shot',
                        action='store_true',
                        help="Display data and exit")
    parser.add_argument('--day-range',
                        action='store',
                        help="Number of days to plot")
    return parser.parse_args()


class WalletParser():

    def __init__(self, rpc_server, days=7):
        self.rpc_server = rpc_server
        self.height = self.get_height()
        self.days = int(days)
        from_block = 5000 * self.days # considering 18 second block is around 4800 block every day
        self.min_height = self.height - from_block if (self.height - from_block) >= 0 else 0
        self.gains = self.populate_history()
        self.daily_gain = self.daily_totals()

        

    def generic_call(self, method, params=None):
        headers = {'Content-Type': 'application/json'}
        body = {"jsonrpc": "2.0",
                "id": "1",
                "method": method,
                "params": params}
        try:
            r = requests.post(self.rpc_server, json=body,
                              headers=headers, timeout=(9, 120))
        except:
            print("RPC not found. Terminating")
            sys.exit()
        return r


    def get_balance(self):
        result = self.generic_call("GetBalance")
        try:
            return json.loads(result.text)['result']['balance']/RATIO
        except:
            print("Fail to get balance from RPC. Terminating")
            sys.exit()
        return None


    def get_height(self):
        result = self.generic_call("GetHeight")
        try:
            return json.loads(result.text)['result']['height']
        except:
            print("Fail to get height from RPC. Terminating")
            sys.exit()
        return None


    def get_transfers(self, param=None):
        result = self.generic_call("GetTransfers", param)
        return json.loads(result.text)


    def clean_date(self, date):
        return parser.parse(date, ignoretz=True).replace(second=0, microsecond=0)


    def discretize_history(self, items, start_date):
        amount_by_minute = dict()
        now = datetime.today().replace(second=0, microsecond=0)
        while start_date <= now:
            amount_by_minute[start_date] = 0
            start_date += timedelta(minutes=1)
        max_height = 0
        for item in items:
            short_date = self.clean_date(item['time'])
            if short_date in amount_by_minute.keys():
                amount_by_minute[short_date] += item['amount']
        return amount_by_minute


    def daily_totals(self):
        items = self.get_transfers({'coinbase': True, 'min_height': self.min_height})['result']['entries']
        start_date = (datetime.today() - timedelta(days=self.days)
                   ).replace(hour=0, minute=0, second=0, microsecond=0)
        amount_by_day = dict()
        now = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        while start_date <= now:
            amount_by_day[start_date] = 0
            start_date += timedelta(days=1)
        while len(amount_by_day) > self.days:
            amount_by_day.pop(min(amount_by_day))
        for item in items:
            short_date = self.clean_date(item['time']).replace(hour=0, minute=0, second=0, microsecond=0)
            if short_date in amount_by_day.keys():
                amount = item['amount']/RATIO
                if amount > 100:
                    continue
                amount_by_day[short_date] += amount
        return amount_by_day


    def populate_history(self):
        coinbase = self.get_transfers({'coinbase': True, 'min_height': self.min_height})
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
        short_hist = self.discretize_history(coinbase['result']['entries'], last_7D)
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


    def update_chart(self, diff):
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        if today == max(self.daily_gain):
            self.daily_gain[today] += diff
        elif today > max(self.daily_gain):
            self.daily_gain.pop(min(self.daily_gain))
            self.daily_gain[today] = diff


    def get_diff(self, height):
        amounts = 0.0
        coinbase = self.get_transfers({'coinbase': True, 'min_height': height})
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


    def update(self):
        diff = 0.0
        current_height = self.get_height()
        if current_height > self.height:
            diff = self.get_diff(self.height)
            self.height = current_height
        self.update_chart(diff)
        for item in self.gains:
            self.gains[item].append(diff)


class DerodParser():

    def __init__(self, rpc_server):
        self.rpc_server=rpc_server
        self.daily_gain=self.avg_diff()

    def generic_call(self, method, params=None):
        headers = {'Content-Type': 'application/json'}
        body = {"jsonrpc": "2.0",
                "id": "1",
                "method": method,
                "params": params}
        try:
            r = requests.post(self.rpc_server, json=body,
                              headers=headers, timeout=(9, 120))
        except:
            print("RPC not found. Terminating")
            sys.exit()
        return r

    def get_block(self, height):
        result = self.generic_call("DERO.GetBlock", {"height": height})
        return json.loads(result.text)

    def get_info(self):
        result = self.generic_call("DERO.GetInfo")
        return json.loads(result.text)

    def get_height(self):
        data = self.generic_call("DERO.GetHeight")
        return json.loads(data.text)['result']['height']

    def avg_diff(self):
        current_height = self.get_height()
        start_date = (datetime.today() - timedelta(days=7)
                   ).replace(hour=0, minute=0, second=0, microsecond=0)
        diff_by_day = dict()
        now = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        while start_date <= now:
            diff_by_day[start_date] = []
            start_date += timedelta(days=1)
        while len(diff_by_day) > 7:
            diff_by_day.pop(min(diff_by_day))
        for i in range(current_height-35000, current_height):
            print(i)
            blk = self.get_block(i)
            short_date = datetime.fromtimestamp(blk['result']['block_header']['timestamp']//1000).replace(hour=0, minute=0, second=0, microsecond=0)
            if short_date in diff_by_day.keys():
                diff_by_day[short_date].append(int(blk['result']['block_header']['difficulty']))
        for item in diff_by_day:
            if len(diff_by_day[item]) == 0:
                diff_by_day[item] = 0
            else:
                diff_by_day[item] = sum(diff_by_day[item])/len(diff_by_day[item])/1000000000
        return diff_by_day



def plot_graph(daily_gain, unit='DERO'):
    colors = {"blue":   "\033[96m",
              "green":  "\033[92m",
              "red":    "033[93m",
            }
    lines = ""
    max_value = max(daily_gain.values())
    count = 0
    for item in daily_gain:
        delimiter = "█" if count%2 == 0 else "░"
        lines += "| {:10}:{:51}{:7.2f} {:4} |\n".format(item.strftime('%Y-%m-%d'), delimiter*(int(daily_gain[item]/max_value*50)), round(daily_gain[item],2), unit)
        count += 1
    return lines


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
        return "\033[96m{:.4f}\033[00m".format(round(sum(data), 4))
    if len(data) == supposed_len:
        return "\033[92m{:.4f}\033[00m".format(round(sum(data), 4))
    return "\033[93m{:.4f}\033[00m".format(round(sum(data), 4))


def compute_power(gain, diff):
    power = dict()
    for item in gain:
        power[item] = (gain[item]/0.06150)*((diff[item]*1000000)/48000)/1000
    return power


def run(rpc_server, max_zero, node_rpc_server=None, one_shot=False, main_rpc=None):
    count_failure = 0
    passing_time = 0
    flag_notify = True
    diff = 0.0
    wp = WalletParser(rpc_server, DAYS)
    node_wp = None if node_rpc_server is None else WalletParser(node_rpc_server)
    dp =  None if main_rpc is None else DerodParser(main_rpc)
    while True:
        lines = ""
        sys.stdout.write("\r")
        lines += "------------------------------------------------------------------------------\n"
        wp.update()
        if node_wp is not None:
            node_wp.update()
        if dp is not None:
            power = compute_power(wp.days, dp.days)
        lines += "|{:^10}:{:^10}:{:^10}:{:^10}:{:^10}:{:^10}:{:^10}|\n".format(
            '', '1m', '15m', '1h', '6h', '24h', '7d')
        lines += "|{:^10}:{:^20}:{:^20}:{:^20}:{:^20}:{:^20}:{:^20}|\n".format('gain',
                                                                               print_sum(
                                                                                   [diff], 1),
                                                                               print_sum(
                                                                                   wp.gains['avg_15'], 15),
                                                                               print_sum(
                                                                                   wp.gains['avg_60'], 60),
                                                                               print_sum(
                                                                                   wp.gains['avg_360'], 360),
                                                                               print_sum(
                                                                                   wp.gains['avg_1440'], 1440),
                                                                               print_sum(
                                                                                   wp.gains['avg_10080'], 10080))
        if node_wp is not None:
            lines += "|{:>10}:{:^20}:{:^20}:{:^20}:{:^20}:{:^20}:{:^20}|\n".format('node gain',
                                                                               print_sum(
                                                                                   [diff], 1),
                                                                               print_sum(
                                                                                   node_wp.gains['avg_15'], 15),
                                                                               print_sum(
                                                                                   node_wp.gains['avg_60'], 60),
                                                                               print_sum(
                                                                                   node_wp.gains['avg_360'], 360),
                                                                               print_sum(
                                                                                   node_wp.gains['avg_1440'], 1440),
                                                                               print_sum(
                                                                                   node_wp.gains['avg_10080'], 10080))
        lines += "|"+" "*76+"|\n"
        if diff == 0.0:
            count_failure += 1
        else:
            count_failure = 0
            flag_notify = True
        lines += "| {:14}:{:59} |\n".format("Current height", wp.height) 
        lines += "| {:14}:{:59f} |\n".format("Wallet amount", wp.get_balance())
        if node_wp is not None:
            lines += "| {:14}:{:59f} |\n".format("Node amount", node_wp.get_balance())
        now = datetime.now()
        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        lines += "| {:14}:{:>59} |\n".format("Date", formatted_date)
        lines += "------------------------------------------------------------------------------\n"
        lines += plot_graph(wp.daily_gain)
        if dp is not None:
            lines += "------------------------------------------------------------------------------\n"
            lines += plot_graph(dp.days, "GH/s")
            lines += "------------------------------------------------------------------------------\n"
            lines += plot_graph(power, "MH/s")
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
        if one_shot:
            sys.exit(0)
        time.sleep(60)
        


if __name__ == '__main__':
    max_zero = 0
    args = get_arguments()
    node_rpc_server = None
    if args.rpc_server:
        wallet_rpc_server = "http://{}/json_rpc".format(args.rpc_server)
    if args.node_rpc_server:
        node_rpc_server = "http://{}/json_rpc".format(args.node_rpc_server)
    if args.tg_bot:
        TELEGRAM_BOT_TOKEN = args.tg_bot
    if args.tg_chat:
        TELEGRAM_CHAT_ID = args.tg_chat
    if args.discord_webhook:
        DISCORD_WEBHOOK = args.discord_webhook
    if args.notify_count:
        max_zero = int(args.notify_count)
    if args.day_range:
        DAYS = args.day_range
    run(wallet_rpc_server, max_zero, node_rpc_server, args.one_shot)#, "http://127.0.0.1:10102/json_rpc")
