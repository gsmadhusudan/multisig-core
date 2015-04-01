"""

"""

__author__ = 'devrandom'

from pycoin.tx.pay_to import build_p2sh_lookup
from pycoin.tx.tx_utils import LazySecretExponentDB
from .oracle import Oracle

def local_sign(tx, scripts, keys):
    """
    Utility for locally signing a multisig transaction

    :param tx:
    :param scripts:
    :param keys:
    :return:
    """
    lookup = None
    if scripts:
        raw_scripts = [script.script() for script in scripts]
        lookup = build_p2sh_lookup(raw_scripts)
        # FIXME hack to work around broken p2sh signing in pycoin
        for i in range(len(tx.unspents)):
            tx.unspents[i].script = raw_scripts[i]
    db = LazySecretExponentDB([key.wif() for key in keys], {})
    tx.sign(db, p2sh_lookup=lookup)


