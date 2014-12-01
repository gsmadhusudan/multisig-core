#!/usr/bin/env python

from __future__ import print_function
import codecs
import io

import sys
import os
import argparse

from pycoin import encoding
from pycoin.serialize import b2h, stream_to_bytes
from pycoin.key import Key
from pycoin.key.BIP32Node import BIP32Node
from pycoin.networks import NETWORK_NAMES
from pycoin.tx.pay_to import ScriptMultisig, build_p2sh_lookup
from pycoin.tx import Tx
from pycoin.tx.tx_utils import LazySecretExponentDB
from pycoin.services import get_tx_db

from digitaloracle import Oracle


def sign(tx, script, key):
    lookup = build_p2sh_lookup([script.script()])
    db = LazySecretExponentDB([key.wif()], {})
    #FIXME hack to work around broken p2sh signing in pycoin
    tx.unspents[0].script = script.script()
    tx.sign(db, p2sh_lookup=lookup)


def main():
    parser = argparse.ArgumentParser(
        description='CryptoCorp digitaloracle command line utility'
    )
    parser.add_argument('-e', '--email')
    parser.add_argument('-n', '--network', default='BTC', choices=NETWORK_NAMES)
    parser.add_argument('-s', "--subkey", help='subkey path (example: 0H/2/15-20)')
    parser.add_argument('-i', "--spendid", help='an additional hex string to disambiguate spends to the same address')
    parser.add_argument('-u', "--baseurl", help='the API endpoint, defaults to https://s.digitaloracle.co/')
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
                    print('could not parse %s %s' % (item, ex), file=sys.stderr)
                    pass
        if tx is None and key is None:
            print('could not understand item %s' % (item))

    oracle = Oracle(keys, tx_db=get_tx_db(), base_url=args.baseurl)

    if args.command == 'dump':
        for key in keys:
            print(key.wallet_key(as_private=False))
    elif args.command == 'create':
        oracle.create(email=args.email)
    elif args.command == 'address':
        oracle.get()
        subkeys = [key.subkey_for_path(args.subkey or "") for key in oracle.all_keys()]
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
            child_key = keys[0].subkey_for_path(args.subkey or "")
            # sign locally
            sign(tx, script, child_key)
            # have Oracle sign
            result = oracle.sign(tx, [args.subkey], [None], spend_id=args.spendid)
            print("Result:")
            print(result)
            if result.has_key('transaction'):
                print("Hex serialized transaction:")
                print(b2h(stream_to_bytes(result['transaction'].stream)))
    else:
        print('unknown command %s' %(args.command), file=sys.stderr)

if __name__ == '__main__':
    main()
