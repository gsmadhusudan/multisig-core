from __future__ import print_function

__author__ = 'sserrano'

import sys
import argparse
from pycoin import encoding
from pycoin.ecdsa import is_public_pair_valid, generator_secp256k1, public_pair_for_x, secp256k1
from pycoin.serialize import b2h, h2b
from pycoin.key import Key
from pycoin.key.BIP32Node import BIP32Node
from pycoin.networks import full_network_name_for_netcode, network_name_for_netcode, NETWORK_NAMES
from pycoin.tx.pay_to import ScriptMultisig
import json
import requests
import uuid

class Error(Exception):
    pass

class OracleError(Error):
    pass

class Oracle(object):
    def __init__(self, keys, manager=None):
        self.keys = keys
        self.manager = manager

    def create(self, email):
        r = {}
        r['walletAgent'] = 'digitaloracle-pycoin-0.01'
        r['rulesetId'] = 'default'
        if self.manager:
            r['managerUsername'] = self.manager
        r['parameters'] = {
            "levels": [
                { "asset": "BTC", "period": 60, "value": 0.001 },
                { "delay": 0, "calls": ['email'] }
            ]
        }
        r['pii'] = {
            'email': email,
        }
        pubkeys = [str(key.wallet_key(as_private=False)) for key in self.keys]
        r['keys'] = pubkeys
        account_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "urn:digitaloracle.co:%s"%(pubkeys[0])))
        body = json.dumps(r)
        url = 'https://s.digitaloracle.co/keychains/' + account_id
        response = requests.post(url, body, headers={'content-type': 'application/json'})

        if response.status_code != 200:
            raise Error("Error contacting oracle")

        result = response.json()
        if result.get('result', None) == 'success':
            oracle_keys = [BIP32Node.from_hwif(s) for s in result['keys']['default']]
            return oracle_keys
        elif result.get('error', None) == 'already exists':
            response = requests.get(url)
            raise OracleError(response.content)
        else:
            raise Error("Unknown response")


