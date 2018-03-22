Crypto Facilities Websocket API v1
==================================

This is a sample web socket application for [Crypto Facilities Ltd](https://www.cryptofacilities.com/), to demonstrate
the new WS API.


Getting Started
---------------

1. Amend the `cfWebSocketApiV1Examples.py` file to enter your api keys
1. Install the required libraries with ```$ pip install -r requirements.txt```
1. Run the example application with ```$ python cfWebSocketApiV1Examples.py```

Functionality Overview
----------------------

* This application subscribes to all available feeds


Application Sample Output
-------------------------

The following is some of what you can expect when running this application:

```
[2018-02-01 20:29:41,968]  [ INFO]  [  Thread-1]  [ cf-ws-api]  Connected to ws://localhost:8080/ws/v1
[2018-02-01 20:29:41,970]  [ INFO]  [  Thread-1]  [ cf-ws-api]  {'event': 'info', 'version': 1}
[2018-02-01 20:29:42,950]  [ INFO]  [MainThread]  [ cf-ws-api]  public subscribe to trade
[2018-02-01 20:29:42,956]  [ INFO]  [  Thread-1]  [ cf-ws-api]  {'event': 'subscribed', 'feed': 'trade', 'product_ids': ['FV_XRPXBT_180615']}
[2018-02-01 20:29:42,974]  [ INFO]  [MainThread]  [ cf-ws-api]  public subscribe to book
[2018-02-01 20:29:42,977]  [ INFO]  [  Thread-1]  [ cf-ws-api]  {'event': 'subscribed', 'feed': 'book', 'product_ids': ['FV_XRPXBT_180615']}
[2018-02-01 20:29:42,978]  [ INFO]  [MainThread]  [ cf-ws-api]  public subscribe to ticker
[2018-02-01 20:29:42,982]  [ INFO]  [  Thread-1]  [ cf-ws-api]  {'feed': 'ticker_snapshot', 'product_id': 'FV_XRPXBT_180615', 'bid': 2.562e-05, 'ask': 0.0, 'bid_size': 5900.0, 'ask_size': 0.0, 'volume': 0.0, 'dtm': 133, 'leverage': '6x', 'index': 0.00010452, 'premium': 0.0, 'last': 2.673e-05, 'time': 1517509363842, 'change': 0.0}
[2018-02-01 20:29:42,982]  [ INFO]  [MainThread]  [ cf-ws-api]  public subscribe to ticker_lite
[2018-02-01 20:29:42,983]  [ INFO]  [  Thread-1]  [ cf-ws-api]  {'event': 'subscribed', 'feed': 'ticker', 'product_ids': ['FV_XRPXBT_180615']}
[2018-02-01 20:29:42,985]  [ INFO]  [  Thread-1]  [ cf-ws-api]  {'event': 'subscribed', 'feed': 'ticker_lite', 'product_ids': ['FV_XRPXBT_180615']}
[2018-02-01 20:29:42,986]  [ INFO]  [  Thread-1]  [ cf-ws-api]  {'feed': 'ticker_lite_snapshot', 'product_id': 'FV_XRPXBT_180615', 'bid': 2.562e-05, 'ask': 0.0, 'change': 0.0, 'premium': 0.0, 'volume': 0.0, 'index': 0.0}
[2018-02-01 20:29:42,990]  [ INFO]  [MainThread]  [ cf-ws-api]  waiting for challenge...
[2018-02-01 20:29:42,997]  [ INFO]  [  Thread-1]  [ cf-ws-api]  {'event': 'challenge', 'message': '5a4ab830-e67f-4c0c-8565-e922f07122fb'}
```