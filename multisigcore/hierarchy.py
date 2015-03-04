from __future__ import print_function
from pycoin.key.BIP32Node import BIP32Node
from pycoin.serialize import h2b

__author__ = 'devrandom'


class AccountKey(BIP32Node):
    @classmethod
    def from_key(cls, key):
        return cls.from_hwif(key)
    def leaf(self, path):
        return self.subkey_for_path(path)


class MasterKey(BIP32Node):
    @classmethod
    def from_seed(cls, master_secret, netcode='BTC'):
        return cls.from_master_secret(master_secret, netcode=netcode)
    @classmethod
    def from_key(cls, key):
        return cls.from_hwif(key)
    def account(self, path):
        return AccountKey.from_key(self.subkey_for_path(path).hwif(as_private=True))