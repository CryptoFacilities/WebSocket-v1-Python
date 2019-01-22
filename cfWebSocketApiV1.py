# Crypto Facilities Ltd Web Socket API V1

# Copyright (c) 2018 Crypto Facilities

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import json
import hashlib
import base64
import hmac
import sys
import websocket

from time import sleep
from threading import Thread
from util.cfLogging import CfLogger

class CfWebSocketMethods(object):
    """Crypto Facilities Ltd Web Socket API Connector"""

    # Special Methods

    def __init__(self, base_url, api_key="", api_secret="", timeout=5, trace=False):
        websocket.enableTrace(trace)
        self.logger = CfLogger.get_logger("cf-ws-api")
        self.base_url = base_url
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout

        self.ws = None
        self.original_challenge = None
        self.signed_challenge = None
        self.challenge_ready = False

        self.__connect()

    # Public feeds
    def subscribe_public(self, feed, product_ids=None):
        """Subscribe to given feed and product ids"""

        if product_ids is None:
            request_message = {
                "event": "subscribe",
                "feed": feed
            }
        else:
            request_message = {
                "event": "subscribe",
                "feed": feed,
                "product_ids": product_ids
            }

        self.logger.info("public subscribe to %s", feed)

        request_json = json.dumps(request_message)
        self.ws.send(request_json)

    def unsubscribe_public(self, feed, product_ids=None):
        """UnSubscribe to given feed and product ids"""


        if product_ids is None:
            request_message = {
                "event": "unsubscribe",
                "feed": feed
            }
        else:
            request_message = {
                "event": "unsubscribe",
                "feed": feed,
                "product_ids": product_ids
            }

        self.logger.info("public unsubscribe to %s", feed)
        request_json = json.dumps(request_message)
        self.ws.send(request_json)

    # Private feeds
    def subscribe_private(self, feed):
        """Unsubscribe to feed"""

        if not self.challenge_ready:
            self.__wait_for_challenge_auth()

        request_message = {"event": "subscribe",
                           "feed": feed,
                           "api_key": self.api_key,
                           "original_challenge": self.original_challenge,
                           "signed_challenge": self.signed_challenge}

        self.logger.info("private subscribe to %s", feed)

        request_json = json.dumps(request_message)
        self.ws.send(request_json)

    def unsubscribe_private(self, feed):
        """Unsubscribe to feed"""

        if not self.challenge_ready:
            self.__wait_for_challenge_auth()

        request_message = {"event": "unsubscribe",
                           "feed": feed,
                           "api_key": self.api_key,
                           "original_challenge": self.original_challenge,
                           "signed_challenge": self.signed_challenge}

        self.logger.info("private unsubscribe to %s", feed)

        request_json = json.dumps(request_message)
        self.ws.send(request_json)

    def __connect(self):
        """Establish a web socket connection"""
        self.ws = websocket.WebSocketApp(self.base_url,
                                         on_message=self.__on_message,
                                         on_close=self.__on_close,
                                         on_open=self.__on_open,
                                         on_error=self.__on_error,
                                         )

        self.wst = Thread(target=lambda: self.ws.run_forever(ping_interval=30))
        self.wst.daemon = True
        self.wst.start()

        # Wait for connect before continuing
        conn_timeout = self.timeout
        while (not self.ws.sock or not self.ws.sock.connected) and conn_timeout:
            sleep(1)
            conn_timeout -= 1

        if not conn_timeout:
            self.logger.info("Couldn't connect to", self.base_url, "! Exiting.")
            sys.exit(1)

    def __on_open(self):
        self.logger.info("Connected to %s", self.base_url)

    def __on_message(self, message):
        """Listen the web socket connection. Block until a message
        arrives. """

        message_json = json.loads(message)
        self.logger.info(message_json)

        if message_json.get("event", "") == "challenge":
                self.original_challenge = message_json["message"]
                self.signed_challenge = self.__sign_challenge(self.original_challenge)
                self.challenge_ready = True

    def __on_close(self):
        self.logger.info('Connection closed')

    def __on_error(self, error):
        self.logger.info(error)

    def __wait_for_challenge_auth(self):
        self.__request_challenge()

        self.logger.info("waiting for challenge...")
        while not self.challenge_ready:
            sleep(1)

    def __request_challenge(self):
        """Request a challenge from Crypto Facilities Ltd"""

        request_message = {
            "event": "challenge",
            "api_key": self.api_key
        }

        request_json = json.dumps(request_message)
        self.ws.send(request_json)

    def __sign_challenge(self, challenge):
        """Signed a challenge received from Crypto Facilities Ltd"""
        # step 1: hash the message with SHA256
        sha256_hash = hashlib.sha256()
        sha256_hash.update(challenge.encode("utf8"))
        hash_digest = sha256_hash.digest()

        # step 3: base64 decode apiPrivateKey
        secret_decoded = base64.b64decode(self.api_secret)

        # step 4: use result of step 3 to has the result of step 2 with HMAC-SHA512
        hmac_digest = hmac.new(secret_decoded, hash_digest, hashlib.sha512).digest()

        # step 5: base64 encode the result of step 4 and return
        sch = base64.b64encode(hmac_digest).decode("utf-8")
        return sch

