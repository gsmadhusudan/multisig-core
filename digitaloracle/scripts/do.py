#!/usr/bin/env python

from __future__ import print_function

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

def create(keys):
    r = {}
    r['walletAgent'] = 'digitaloracle-pycoin-0.01'
    r['rulesetId'] = 'default'
    r['parameters'] = {
            "levels": [ { "asset": "BTC", "period": 60, "value": 0.001 },
                { "delay": 0, "calls": ['email'] } ]
            }
    r['pii'] = { 'email': 'c1.github@niftybox.net' }
    pubkeys = [str(key.wallet_key(as_private=False)) for key in keys]
    r['keys'] = pubkeys
    account_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "urn:digitaloracle.co:%s"%(pubkeys[0])))
    body = json.dumps(r)
    url = 'https://s.digitaloracle.co/keychains/' + account_id
    response = requests.post(url, body, headers={'content-type': 'application/json'})
    #print(response.status_code)
    result = response.json()
    if result.get('result', None) == 'success':
        print('success')
    elif result.get('error', None) == 'already exists':
        print('exists')
        response = requests.get(url)
        result = response.json()
    #print(result)
    oracle_keys = [BIP32Node.from_hwif(s) for s in result['keys']['default']]
    keys = keys + oracle_keys
    return keys

def main():
    parser = argparse.ArgumentParser(
        description='CryptoCorp digitaloracle command line utility'
    )
    parser.add_argument('-n', '--network', default='BTC', choices=NETWORK_NAMES)
    parser.add_argument('-s', "--subkey", help='subkey path (example: 0H/2/15-20)')
    parser.add_argument('command')
    parser.add_argument('item', nargs='+')
    args = parser.parse_args()

    keys = []
    for item in args.item:
        key = None
        if item.startswith('P:'):
            s = item[2:]
            key = BIP32Node.from_master_secret(s.encode('utf8'), netcode=args.network)
        else:
            key = Key.from_text(item)
        keys.append(key)
    if args.command == 'dump':
        for key in keys:
            print(key.wallet_key(as_private=False))
    elif args.command == 'create':
        keys = create(keys)
        subkeys = [key.subkey_for_path(args.subkey or "") for key in keys]
        for key in subkeys:
            print(key.wallet_key(as_private=False))
        secs = [key.sec() for key in subkeys]
        secs.sort()
        print([b2h(s) for s in secs])
        script = ScriptMultisig(2, secs)
        #import pdb; pdb.set_trace()
        print(script.address(netcode=args.network))
    else:
        print('unknown command %s' %(args.command), file=sys.stderr)

if __name__ == '__main__':
    main()
