#!/usr/bin/env python

from __future__ import print_function

import pdb
import sys
import os
import argparse
from pycoin import encoding
from pycoin.ecdsa import is_public_pair_valid, generator_secp256k1, public_pair_for_x, secp256k1
from pycoin.serialize import b2h, h2b, stream_to_bytes
from pycoin.key import Key
from pycoin.key.BIP32Node import BIP32Node
from pycoin.networks import full_network_name_for_netcode, network_name_for_netcode, NETWORK_NAMES
from pycoin.tx.pay_to import ScriptMultisig, build_p2sh_lookup
from pycoin.tx import Tx
from pycoin.tx.tx_utils import LazySecretExponentDB
import json
import requests
import uuid

def sign(tx, script, key):
    #pdb.set_trace()
    lookup = build_p2sh_lookup([script.script()])
    tx.sign(LazySecretExponentDB([key.wif()], {}), p2sh_lookup=lookup)

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
    txs = []
    for item in args.item:
        key = None
        tx = None
        if item.startswith('P:'):
            s = item[2:]
            key = BIP32Node.from_master_secret(s.encode('utf8'), netcode=args.network)
            keys.append(key)
        else:
            try:
                key = Key.from_text(item)
                keys.append(key)
            except encoding.EncodingError:
                pass
        if key is None:
            if os.path.exists(item):
                try:
                    with open(item, "rb") as f:
                        if f.name.endswith("hex"):
                            f = io.BytesIO(codecs.getreader("hex_codec")(f).read())
                        tx = Tx.parse(f)
                        txs.append(tx)
                        try:
                            tx.parse_unspents(f)
                        except Exception as ex:
                            pass
                        continue
                except Exception:
                    pass

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
        print(script.address(netcode=args.network))
    elif args.command == 'sign':
        keys = create(keys)
        subkeys = [key.subkey_for_path(args.subkey or "") for key in keys]
        secs = [key.sec() for key in subkeys]
        secs.sort()
        script = ScriptMultisig(2, secs)
        print(script.address(netcode=args.network))
        for tx in txs:
            print(tx.id())
            print(b2h(stream_to_bytes(tx.stream)))
            print('scripts:')
            for inp in tx.txs_in:
                print('- %s'%(inp.script))
            sign(tx, script, subkeys[0])
            print(b2h(stream_to_bytes(tx.stream)))

    else:
        print('unknown command %s' %(args.command), file=sys.stderr)

if __name__ == '__main__':
    main()
