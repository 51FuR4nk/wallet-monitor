# wallet-monitor
Dero HE Wallet Monitor. Statistics and more

This script aims to show some statistics about the Dero mined from a node.
```
------------------------------------------------------------------------------
|          :    1m    :   15m    :    1h    :    6h    :   24h    :    7d    |
|   gain   :    0     :  0.123   :  0.246   :  4.7367  : 18.7608  : 76.1967  |
|                                                                            |
| Current height:                                                      27374 |
| Current amount:                                                  75.025960 |
| Date:                                                  2022-03-04 23:25:24 |
------------------------------------------------------------------------------
| 2022-02-25:                                                    0.0000 DERO |
| 2022-02-26:                                                    0.0000 DERO |
| 2022-02-27:■                                                   0.0615 DERO |
| 2022-02-28:■■■■■■■■                                            0.4920 DERO |
| 2022-03-01:■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■                      1.8450 DERO |
| 2022-03-02:■■■■■■■■■■                                          0.6150 DERO |
| 2022-03-03:■■■■                                                0.2460 DERO |
| 2022-03-04:■■                                                  0.1230 DERO |
------------------------------------------------------------------------------
```
The information are retrieved by the wallet history and contains only the data about the mining (coinbase tx).
Info are updated every 60 seconds.

Due to some rounding the script is not 100% accurate but it will get better in the future.


## Requirements

1. Python 3
2. A running dero wallet with the --rpc-server on. **This must be the wallet you are mining on or receiving the node reward.** If the wallet close or is terminated the script will terminate as well.
e.g.
```
./dero-wallet-cli-linux-amd64 --unlock --remote --rpc-server
```

Pip library required:
```
pip3 install beepy
pip3 install python-dateutil
```

## Installation
```
git clone https://github.com/51FuR4nk/wallet-monitor.git
```
or just copy and paste derohe_monitor.py

## Usage
run the code with
```
python3 derohe_monitor.py
```

```
usage: python3 {'prog': 'derohe_monitor.py'} [-a]

optional arguments:
  -h, --help            show this help message and exit
  --rpc-server RPC_SERVER
                        Wallet rpc-server address. Default 127.0.0.1:10103
  --node-rpc-server NODE_RPC_SERVER
                        Node wallet rpc-server address.
  --tg-bot TG_BOT       Telegram bot token
  --tg-chat TG_CHAT     Telegram chat id
  --discord-webhook DISCORD_WEBHOOK
                        Discord webhook url
  --notify-count NOTIFY_COUNT
                        Notify if you don't get reward after X minutes. defult
                        disabled
  --one-shot            Display data and exit
  --day-range DAY_RANGE
                        Number of days to plot. Default 7
  --sound               Play sound when a new miniblock is found
```

Option are for:
- specify the RPC server if not the default one
- have notification on TG if you don receive reward for X minute. For this funcion 3 parameters net to be set (--tg-bot, --tg-chat, --notify-count)
- one shot, will plot the graph and exit
- day-range will plot an arbitrary number of days. Default is 7

## Notes

1. This script have been tested on linux only, please report any issue with other systems.
2. wait some time after starting your wallet before starting the script. Sometimes the RPC respond with random stuff when is started.
