#!/usr/bin/env python

from __future__ import print_function

from pdb import set_trace
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
from digitaloracle import Oracle
from pycoin.services import get_tx_db

def sign(tx, script, key):
    lookup = build_p2sh_lookup([script.script()])
    tx.sign(LazySecretExponentDB([key.wif()], {}), p2sh_lookup=lookup)

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
                except Exception as ex:
                    print('could not parse %s %s' %(item, ex), file=sys.stderr)
                    pass

    oracle = Oracle(keys, tx_db=get_tx_db())

    if args.command == 'dump':
        for key in keys:
            print(key.wallet_key(as_private=False))
    elif args.command == 'create':
        oracle.create()
        subkeys = [key.subkey_for_path(args.subkey or "") for key in keys]
        for key in subkeys:
            print(key.wallet_key(as_private=False))
        secs = [key.sec() for key in subkeys]
        secs.sort()
        print([b2h(s) for s in secs])
        script = ScriptMultisig(2, secs)
        print(script.address(netcode=args.network))
    elif args.command == 'sign':
        oracle.get()
        script = oracle.script(args.subkey)
        print(script.address(netcode=args.network))
        for tx in txs:
            print(tx.id())
            print(b2h(stream_to_bytes(tx.stream)))
#            print('scripts:')
#            for inp in tx.txs_in:
#                print('- %s'%(inp.script))
            subkey = keys[0].subkey_for_path(args.subkey or "")
            sign(tx, script, subkey)
            oracle.sign(tx, [args.subkey], [None])
            print(b2h(stream_to_bytes(tx.stream)))

    else:
        print('unknown command %s' %(args.command), file=sys.stderr)

if __name__ == '__main__':
    main()
