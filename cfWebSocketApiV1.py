# Simple Web Socket client application
# 5 Jan 2018 theo@cryptofacilities.co.uk

import json
import hashlib
import base64
import hmac
import sys
import websocket

from time import sleep
from threading import Thread

import settings
from util.cfLogging import CfLogger
from util.utils import is_not_valid_feed, is_public_feed
from util.utils import SUBSCRIBE_EVENT, UNSUBSCRIBE_EVENT, CHALLENGE_EVENT


class CfWebSocket:
    """Crypto Facilities Ltd Web Socket API Connector"""

    # Special Methods

    def __init__(self, exchange, base_url, api_key="", api_secret="", check_certificate=True, buffer=None):
        self.logger = CfLogger.get_logger(" cf-ws-api ")
        self.exchange = exchange
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.nonce = 0
        self.check_certificate = check_certificate

        # Interprocess communication buffer. Receive new callbacks from mm thread
        self.callbacks_buffer = buffer

        # Store callbacks that read from buffer
        self.callbacks = {}  # {(feed,product_ids):  [callbacks]} or  {feed:  [callbacks]}

        # Active subscriptions
        self.public_subscriptions = {"trade": [], "book": [], "ticker": [], "ticker_lite": []}
        self.private_subscriptions = []  # [feed_a, feed_b]

        self.conn = None
        self.original_challenge = None
        self.signed_challenge = None
        self.connected = False

    # Public Methods

    def subscribe(self, feed="", product_ids=None):
        """Subscribe to feeds to receive real-time information.
        Subscriptions are cached so subscribing twice will fail
        silently"""
        if product_ids is None:
            product_ids = []

        if is_not_valid_feed(feed):
            self.logger.error('subscribe(): Cannot subscribe to invalid feed')
            return

        if is_public_feed(feed):
            not_subscribed_prods = list(set(product_ids) - set(self.public_subscriptions[feed]))
            # Subscribe only if not already subscribed to this <feed,product>
            if not_subscribed_prods:
                self.__subscribe_no_auth(feed, product_ids)
                self.public_subscriptions[feed] += not_subscribed_prods

        else:
            # Subscribe only if not already subscribed to this feed
            if feed not in self.private_subscriptions:
                self.__subscribe_with_api_key(feed)
                self.private_subscriptions.append(feed)

    def unsubscribe(self, feed="", product_ids=None):
        """Unsubscribe from feeds"""
        if product_ids is None:
            product_ids = []

        if is_not_valid_feed(feed):
            self.logger.error('unsubscribe(): Cannot unsubscribe to invalid feed')
            return

        if is_public_feed(feed):
            self.__unsubscribe_no_auth(feed, product_ids)
            self.public_subscriptions[feed] = [x for x in self.public_subscriptions[feed] if x not in product_ids]

        else:
            if feed in self.private_subscriptions:
                self.__unsubscribe_with_api_key(feed)
                self.private_subscriptions.remove(feed)

    def exit(self):
        self.connected = False
        self.conn.close()

    # Private Methods
    def connect(self):
        """Establish Web Socket connection """
        try:
            self.logger.debug("Creating connection to %s", self.base_url)
            # self.conn = create_connection(self.base_url)
            self.__connect()
        except:
            self.exit()
            return

    def __connect(self):
        """Establish a web socket connection"""
        self.conn = websocket.WebSocketApp(self.base_url,
                                           on_message=self.__on_message,
                                           on_close=self.__on_close,
                                           on_open=self.__on_open,
                                           on_error=self.__on_error,
                                           )

        self.wst = Thread(target=lambda: self.conn.run_forever())
        self.wst.daemon = True
        self.wst.start()

        # Wait for connect before continuing
        conn_timeout = 5
        while (not self.conn.sock or not self.conn.sock.connected) and conn_timeout:
            sleep(1)
            conn_timeout -= 1

        if not conn_timeout:
            self.logger.error("Couldn't connect to %s! Exiting.", self.base_url)
            self.exit()
            sys.exit(1)

    def __on_open(self, conn):
        self.logger.debug("Started waiting for messages ...")
        self.connected = True

        while True:
            self.__request_challenge()
            print(self.original_challenge)
            sleep(1)

    def __on_message(self, conn, message):
        """Listen the web socket connection. Block until a message
        is arrive"""

        message_json = json.loads(message)

        if "event" in message_json:
            if message_json['event'] == "error":
                self.logger.error("Web Socket respond with error -> %s", message_json)

            elif message_json['event'] == "info":
                # If key and secret are given request a challenge
                if self.api_key and self.api_secret:
                    self.__request_challenge()
            # When receive challenge sign it and cache it to send it along with every private message
            elif message_json["event"] == CHALLENGE_EVENT:
                self.original_challenge = message_json["message"]
                self.signed_challenge = self.__sign_challenge()

            else:
                self.__handle_subscription_message(message_json)

        else:
            self.__handle_feed_message(message_json)

    def __on_close(self, conn):
        self.logger.debug('Connection closed')
        self.exit()

    def __on_error(self, conn, error):
        self.logger.error(error)
        self.exit()

    # Auth mechanism

    def __request_challenge(self):
        """Request a challenge from Crypto Facilities Ltd"""
        data = json.dumps({"event": "challenge", "api_key": self.api_key})
        self.logger.debug("Requesting challenge with -> %s", data)
        self.conn.send(data)

    def __sign_challenge(self):
        """Signed a challenge received from Crypto Facilities Ltd"""
        # step 1: hash the message with SHA256
        sha256_hash = hashlib.sha256()
        sha256_hash.update(self.original_challenge.encode("utf8"))
        hash_digest = sha256_hash.digest()

        # step 3: base64 decode apiPrivateKey
        secret_decoded = base64.b64decode(self.api_secret)

        # step 4: use result of step 3 to has the result of step 2 with HMAC-SHA512
        hmac_digest = hmac.new(secret_decoded, hash_digest, hashlib.sha512).digest()

        # step 5: base64 encode the result of step 4 and return
        sch = base64.b64encode(hmac_digest).decode("utf-8")
        self.logger.debug("Signed challenge: %s -> %s", self.original_challenge, sch)
        return sch

    def __subscribe_no_auth(self, feed, product_ids):
        data = {"event": SUBSCRIBE_EVENT, "feed": feed, "product_ids": product_ids}
        self.logger.debug("No auth subscribe to %s with -> %s", feed, data)
        self.conn.send(json.dumps(data))

    def __unsubscribe_no_auth(self, feed, product_ids):
        data = {"event": UNSUBSCRIBE_EVENT, "feed": feed, "product_ids": product_ids}
        self.logger.debug("No auth unsubscribe to %s with -> %s", feed, data)
        self.conn.send(json.dumps(data))

    def __subscribe_with_api_key(self, feed):
        data = {"event": SUBSCRIBE_EVENT, "feed": feed, "api_key": self.api_key,
                "original_challenge": self.original_challenge, "signed_challenge": self.signed_challenge}
        self.logger.debug("Api Key subscribe to %s with -> %s", feed, data)
        self.conn.send(json.dumps(data))

    def __unsubscribe_with_api_key(self, feed):
        data = {"event": UNSUBSCRIBE_EVENT, "feed": feed, "api_key": self.api_key,
                "original_challenge": self.original_challenge, "signed_challenge": self.signed_challenge}
        self.logger.debug("Api Key unsubscribe to %s with -> %s", feed, data)
        self.conn.send(json.dumps(data))

    def __handle_subscription_message(self, message):
        """Handle subscription responses in this thread. Do not fill
        the message queue with redundant information"""

        if message['event'] == "subscribed":
            self.logger.debug("Successful subscribe with -> %s", message)
        elif message['event'] == "unsubscribed":
            self.logger.debug("Successful unsubscribe with -> %s", message)
        elif message['event'] == "subscribe_failed":
            self.logger.error("Subscribe failed with -> %s", message)

    def __handle_feed_message(self, message):
        """Receive message from feed. Read the callback events and execute
        those that match the received feed message"""

        if "snapshot" in message["feed"]:
            self.logger.debug("Received snapshot -> %s", message)
            return
        else:
            self.logger.debug("Received -> %s", message)
            self.__read_callbacks()
            self.__execute_callbacks(message["feed"], message)

    def __read_callbacks(self):
        while not self.callbacks_buffer.empty():
            callback_message = self.callbacks_buffer.get()
            action = callback_message["action"]

            if action == "add":
                self.__add_callback(callback_message)
            elif action == "remove":
                self.__remove_callback(callback_message)
            else:
                self.logger.error("__read_callbacks(): callback message.")

    def __execute_callbacks(self, feed, message):
        """Execute the register callback"""
        callbacks = self.__get_callbacks(feed, message)

        if not callbacks:
            return

        for callback in callbacks:
            callback_fn = callback["callback_fn"]
            kwargs = callback["kwargs"]

            # Trigger callbacks when receive information about a trade
            if feed == "trade":
                trade = message
                self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                callback_fn(self.exchange, trade, **kwargs)

            # Trigger callbacks when receive information about a book entry
            elif feed == "book":
                book_entry = message
                self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                callback_fn(self.exchange, book_entry, **kwargs)

            # Trigger callbacks when receive information about a ticker
            elif feed == "ticker":

                ticker = message
                self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                callback_fn(self.exchange, ticker, **kwargs)

            # Trigger callbacks when receive information about margin account
            elif feed == "account_balances_and_margins":
                margin_accounts = message["margin_accounts"]
                for m_account in margin_accounts:
                    self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                    callback_fn(self.exchange, m_account, **kwargs)

            # Trigger callbacks when receive information about an account log
            elif feed == "account_log":
                logs = message["logs"]
                for log in logs:
                    self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                    callback_fn(self.exchange, log, **kwargs)

            # Trigger callbacks when receive information about an account deposit/withdrawal
            elif feed == "deposits_withdrawals":
                transactions = message["elements"]
                for transaction in transactions:
                    self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                    callback_fn(self.exchange, transaction, **kwargs)

            # Trigger callbacks when receive information about an order fill
            elif feed == "fills":
                fills = message["fills"]
                for fill in fills:
                    self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                    callback_fn(self.exchange, fill, **kwargs)

            # Trigger callbacks when receive information about a position
            elif feed == "open_positions":
                open_positions = message["open_positions"]
                for pos in open_positions:
                    self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                    callback_fn(self.exchange, pos, **kwargs)

            # Trigger callbacks when receive information about an order
            elif feed == "open_orders":
                is_cancel = message["is_cancel"]
                if is_cancel:
                    return

                order = message["order"]
                self.logger.debug("Executing %s callback event -> %s", feed, callback_fn.__name__)
                callback_fn(self.exchange, order, **kwargs)

    def __get_callbacks(self, feed, message):
        if is_public_feed(feed):
            product_id = message["product_id"]
            key = (feed, product_id)
        else:
            key = feed

        return self.callbacks.get(key, [])

    def __add_callback(self, callback_message):
        """Adds a feed callback. If feed is public it will create one entry
        per product id"""
        feed = callback_message["feed"]
        callback_fn = callback_message["callback_fn"]
        kwargs = callback_message["kwargs"]

        if is_public_feed(feed):
            product_ids = callback_message["product_ids"]

            for product_id in product_ids:
                key = (feed, product_id)
                if key not in self.callbacks:
                    self.callbacks[key] = []

                callback = {"callback_fn": callback_fn, "kwargs": kwargs}
                self.callbacks[key].append(callback)
                self.logger.debug("callback added -> %s", callback)
        else:
            key = feed
            if key not in self.callbacks:
                self.callbacks[key] = []

            callback = {"callback_fn": callback_fn, "kwargs": kwargs}
            self.callbacks[feed].append(callback)
            self.logger.debug("callback added -> %s", callback)

    def __remove_callback(self, callback_message):
        """Removes a register callback on a (feed,product) if feed is public and
        on a feed if feed is private. On a public feed unregister, the callback will
         be remove for every product id that it was passed in a list as a callback value"""

        feed = callback_message["feed"]
        callback_fn = callback_message["callback_fn"]

        if is_public_feed(feed):
            product_ids = callback_message["product_ids"]

            # Remove the callback from each (feed,product) pair
            for product_id in product_ids:
                public_callbacks = self.callbacks.get((feed, product_id), [])

                for callback in public_callbacks:
                    if callback["callback_fn"].__name__ == callback_fn:
                        public_callbacks.remove(callback)
                        self.logger.debug("callback removed -> %s", callback)

                # No subscription needed when no callbacks exist for (feed,product)
                if not public_callbacks:
                    self.logger.debug("Unnecessary subscription found, unsubscribing from (%s,%s)", feed, [product_id])
                    self.unsubscribe(feed=feed, product_ids=[product_id])
        else:
            # Remove the callback from feed
            private_callbacks = self.callbacks.get(feed, [])
            for callback in private_callbacks:
                if callback["callback_fn"].__name__ == callback_fn:
                    private_callbacks.remove(callback)
                    self.logger.debug("callback removed -> %s", callback)

            # No subscription needed when no callbacks exist for feed
            if not private_callbacks:
                self.logger.debug("Unnecessary subscription found, unsubscribing from %s", feed)
                self.unsubscribe(feed=feed)