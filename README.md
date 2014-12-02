CryptoCorp's digitaloracle API implementation using the pycoin library.

Currently this requires the `p2sh` branch of `https://github.com/devrandom/pycoin.git`.

Examples
===
```bash
    export PYCOIN_CACHE_DIR=~/.pycoin_cache
    export PYCOIN_SERVICE_PROVIDERS=BLOCKR_IO:BLOCKCHAIN_INFO:BITEASY:BLOCKEXPLORER

    digitaloracle --email a@b.com create P:aaa P:bbb
       # not recommended - both keys on one machine

    digitaloracle --email a@b.com create P:aaa xpub...

    digitaloracle -s 0/0/123 address P:aaa xpub...
       # shows deposit address

    tx -i SOURCE_ADDRESS DESTINATION_ADDRESS -o tx.bin

    digitaloracle -s 0/0/123 sign P:aaa xpub...
       # signs and shows tx hex)
```
