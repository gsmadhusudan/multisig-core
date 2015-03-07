BitOasis / CryptoCorp's Multisig python API implementation using the pycoin library.

Currently this requires the `p2sh` branch of `https://github.com/devrandom/pycoin.git`.

Examples
===
```bash
    export PYCOIN_CACHE_DIR=~/.pycoin_cache
    export PYCOIN_SERVICE_PROVIDERS=BLOCKR_IO:BLOCKCHAIN_INFO:BITEASY:BLOCKEXPLORER

    digital_oracle --email a@b.com create P:aaa P:bbb
       # not recommended - both keys on one machine

    digital_oracle --email a@b.com create P:aaa xpub...

    digital_oracle -i 0/0/123 address P:aaa xpub...
       # shows deposit address

    tx -i SOURCE_ADDRESS DESTINATION_ADDRESS -o tx.bin

    digital_oracle sign P:aaa xpub... tx.bin -i 0/0/123
       # signs and shows tx hex)

    digital_oracle sign P:aaa xpub... tx.bin -i 0/0/123 0/0/124 -c - 0/1/44
       # signs tx with two inputs and two outputs.  The second output is change.
```
