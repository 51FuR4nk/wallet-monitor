# wallet-monitor
Dero HE Wallet Monitor. Statistics and more

This script aims to show some statistics about the Dero mined from a node.
```
------------------------------------------------------------------------------
|          :    1m    :   15m    :    1h    :    6h    :   24h    :    7d    |
| tot gain :    0     :  0.0615  :  0.492   :  4.551   : 23.5608  : 57.4359  |
|                                                                            |
| Current amount:                                                  56.511130 |
| Date:                                                  2022-03-03 23:28:48 |
------------------------------------------------------------------------------
```
The information are retrieved by the wallet history and contains only the data about the mining (coinbase tx).
Info are updated every 60 seconds.

Due to some rounding the script is not 100% accurate but it will get better in the future.


## Requirements

1. Python 3
2. A running dero wallet with the --rpc-server on. **This must be the wallet you are mining on or receiving the node reward.**
e.g.
```
./dero-wallet-cli-linux-amd64 --unlock --remote --rpc-server
```

## Installation
```
git clone git@github.com:51FuR4nk/wallet-monitor.git
```
or just copy and paste derohe_monitor.py

## Usage
```
usage: python3 {'prog': 'derohe_monitor.py'} [-a]

DeroHE wallet monitor

optional arguments:
  -h, --help            show this help message and exit
  --rpc-server RPC_SERVER
                        rpc-server address. Default 127.0.0.1:10109
  --tg-bot TG_BOT       Telegram bot token
  --tg-chat TG_CHAT     Telegram chat id
  --notify-count NOTIFY_COUNT
                        Notify if you don't get reward after X minutes. defult
                        disabled
```

Option are for:
- specify the RPC server if not the default one
- have notification on TG if you don receive reward for X minute. For this funcion 3 parameters net to be set (--tg-bot, --tg-chat, --notify-count)

## Discalimer

This script have been tested on linux only, please report any issue with other systems.
