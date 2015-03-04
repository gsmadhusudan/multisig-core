from __future__ import print_function
from pycoin import encoding
from pycoin.key.BIP32Node import BIP32Node
from pycoin.tx.pay_to import ScriptMultisig, ScriptPayToScript

__author__ = 'devrandom'


class AccountKey(BIP32Node):
    @classmethod
    def from_key(cls, key):
        return cls.from_hwif(key)

    def leaf(self, n, change=False):
        return self.leaf_for_path("%s/%s" % (n, 1 if change else 0))

    def leaf_for_path(self, path):
        return self.subkey_for_path(path)


class MasterKey(BIP32Node):
    @classmethod
    def from_seed(cls, master_secret, netcode='BTC'):
        return cls.from_master_secret(master_secret, netcode=netcode)

    @classmethod
    def from_key(cls, key):
        return cls.from_hwif(key)

    def account_for_path(self, path):
        return AccountKey.from_key(self.subkey_for_path(path).hwif(as_private=True))

    def electrum_account(self, n):
        return self.account_for_path("0H/%s" % (n,))

    def bip32_account(self, n):
        return self.account_for_path("%sH" % (n,))

    def bip44_account(self, n, purpose=0, coin=0):
        return self.account_for_path("%sH/%sH/%sH" % (purpose, coin, n))


class MultisigAccount:
    def __init__(self, keys, num_sigs=None, complete=True):
        """
        Create an Oracle object

        :param keys: non-oracle deterministic keys
        :type keys: list[BIP32Node]
        :param num_sigs: number of required signatures
        :param complete: whether we need additional keys to complete the configuration of this account
        """
        self.keys = keys
        self.public_keys = [str(key.wallet_key(as_private=False)) for key in self.keys]
        self.num_sigs = num_sigs if num_sigs else len(keys) - 1
        self.complete = complete

    def add_key(self, key):
        if self.complete:
            raise Exception("account already complete")
        self.keys.append(key)
        self.public_keys.append(key.wallet_key(as_private=False))

    def add_keys(self, keys):
        for key in keys:
            self.add_key(key)

    def set_complete(self):
        if self.complete:
            raise Exception("account already complete")
        self.complete = True

    def leaf_script(self, n, change=False):
        return self.script_for_path("%s/%s" % (n, 1 if change else 0))

    def leaf_payto(self, n, change=False):
        return self.payto_for_path("%s/%s" % (n, 1 if change else 0))

    def script_for_path(self, path):
        """Get the redeem script for the path.  The multisig format is (n-1) of n, but can be overridden.

        :param: path: the derivation path
        :type: path: str
        :return: the script
        :rtype: ScriptMultisig
        """
        subkeys = [key.subkey_for_path(path or "") for key in self.keys]
        secs = [key.sec() for key in subkeys]
        secs.sort()
        script = ScriptMultisig(self.num_sigs, secs)
        return script

    def payto_for_path(self, path):
        """Get the payto script for the path.  See also :meth:`.script`

        :param: path: the derivation path
        :type: path: str
        :return: the script
        :rtype: ScriptPayToScript
        """
        script = self.script_for_path(path)
        payto = ScriptPayToScript(hash160=encoding.hash160(script.script()))
        return payto
