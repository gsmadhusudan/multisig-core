from __future__ import print_function
import io

from pycoin import encoding
from pycoin.key.BIP32Node import BIP32Node
from pycoin.scripts.tx import DEFAULT_VERSION
from pycoin.serialize import h2b
from pycoin.services import providers
from pycoin.tx import Tx, Spendable, TxOut
from pycoin.tx.TxOut import standard_tx_out_script
from pycoin.tx.pay_to import ScriptMultisig, ScriptPayToScript


__author__ = 'devrandom'

LOOKAHEAD = 20
DUST = 546


class AccountKey(BIP32Node):
    @classmethod
    def from_key(cls, key):
        return cls.from_hwif(key)

    def leaf(self, n, change=False):
        return self.leaf_for_path("%s/%s" % (n, 1 if change else 0))

    def leaf_for_path(self, path):
        return self.subkey_for_path(path)


class MasterKey(BIP32Node):
    """Master key (m or M)"""
    @classmethod
    def from_seed(cls, master_secret, netcode='BTC'):
        return cls.from_master_secret(master_secret, netcode=netcode)

    @classmethod
    def from_seed_hex(cls, master_secret_hex, netcode='BTC'):
        return cls.from_seed(h2b(master_secret_hex), netcode)

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


class ElectrumMasterKey(BIP32Node):
    """Electrum 'Master' key (m/0' or M/0').  Normally used for external Electrum keychains that are
    participating in a multisig relationship"""
    @classmethod
    def from_key(cls, key):
        return cls.from_hwif(key)

    def account_for_path(self, path):
        return AccountKey.from_key(self.subkey_for_path(path).hwif())

    def electrum_account(self, n):
        return self.account_for_path("%s" % (n,))

TX_FEE_PER_THOUSAND_BYTES = 1000


def recommended_fee_for_tx(tx):
    """
    Return the recommended transaction fee in satoshis.
    This is a grossly simplified version of this function.
    TODO: improve to consider TxOut sizes.
      - whether the transaction contains "dust"
      - whether any outputs are less than 0.001
    """
    # FIXME review
    s = io.BytesIO()
    tx.stream(s)
    tx_byte_count = len(s.getvalue())
    tx_fee = TX_FEE_PER_THOUSAND_BYTES * ((999+tx_byte_count)//1000)
    return tx_fee


class Account(object):
    __slots__ = ['num_ext_keys', 'num_int_keys', 'netcode', '_provider']

    def __init__(self, netcode='BTC', num_ext_keys=None, num_int_keys=None):
        if num_ext_keys is None:
            num_ext_keys = 1
        if num_int_keys is None:
            num_int_keys = 1
        object.__setattr__(self, 'num_ext_keys', num_ext_keys)
        object.__setattr__(self, 'num_int_keys', num_int_keys)
        object.__setattr__(self, 'netcode', netcode)
        self._provider = providers

    def address(self, n, change=False):
        raise NotImplementedError()

    def addresses(self):
        addresses = [self.address(n, False) for n in range(0, self.num_ext_keys)]
        addresses.extend([self.address(n, True) for n in range(0, self.num_int_keys)])
        return addresses

    def spendables(self):
        """
        :return:
        :rtype: list[Spendable]
        """
        addresses = self.addresses()
        spendables = []
        for addr in addresses:
            spendables.extend(self._provider.spendables_for_address(addr))

        return spendables

    def balance(self):
        spendables = self.spendables()
        total = reduce(lambda x,y: x+y, [s.coin_value for s in spendables])
        return total

    def tx(self, payables):
        """
        :param list[(str, int)] payables: tuple of address and amount
        :return Tx or None: the transaction or None if not enough balance
        """
        all_spendables = self.spendables()

        send_amount = 0
        for address, coin_value in payables:
            send_amount += coin_value

        txs_out = []
        for address, coin_value in payables:
            script = standard_tx_out_script(address)
            txs_out.append(TxOut(coin_value, script))

        total = 0
        txs_in = []
        spendables = []
        while total < send_amount and all_spendables:
            spend = all_spendables.pop(0)
            spendables.append(spend)
            txs_in.append(spend.tx_in())
            total += spend.coin_value

        tx_for_fee = Tx(txs_in=txs_in, txs_out=txs_out, version=DEFAULT_VERSION, unspents=spendables)
        fee = recommended_fee_for_tx(tx_for_fee)

        while total < send_amount + fee and all_spendables:
            spend = all_spendables.pop(0)
            spendables.append(spend)
            txs_in.append(spend.tx_in())
            total += spend.coin_value

        if total > send_amount + fee + DUST:
            script = standard_tx_out_script(self.current_change_address())
            txs_out.append(TxOut(total - send_amount - fee, script))
        elif total < send_amount + fee:
            return None

        # check total >= amount + fee
        tx = Tx(txs_in=txs_in, txs_out=txs_out, version=DEFAULT_VERSION, unspents=spendables)
        return tx

    def current_address(self):
        return self.address(self.num_ext_keys - 1)

    def current_change_address(self):
        return self.address(self.num_int_keys - 1, True)

class SimpleAccount(Account):
    __slots__ = ['_key']

    def __init__(self, key, netcode='BTC', num_ext_keys=None, num_int_keys=None):
        """
        :param key:
        :type key: AccountKey
        """
        super(SimpleAccount, self).__init__(netcode, num_ext_keys, num_int_keys)
        self._key = key

    def address(self, n, change=False):
        return self._key.subkey_for_path("%s/%s" % (n, 1 if change else 0)).address(self.netcode)


class MultisigAccount(Account):
    def __init__(self, keys, num_sigs=None, sort=True, complete=True, netcode='BTC', num_ext_keys=None, num_int_keys=None):
        """
            Create a multisig account with multiple participating keys

            :param keys: non-oracle deterministic keys
            :type keys: list[BIP32Node]
            :param num_sigs: number of required signatures
            :param complete: whether we need additional keys to complete the configuration of this account
            """
        super(MultisigAccount, self).__init__(netcode, num_ext_keys, num_int_keys)
        self._keys = keys
        self._public_keys = [str(key.wallet_key(as_private=False)) for key in self._keys]
        self._num_sigs = num_sigs if num_sigs else len(keys) - (1 if complete else 0)
        self._complete = complete
        self._sort = sort

    @property
    def complete(self):
        return self._complete

    @property
    def public_keys(self):
        return self._public_keys

    @property
    def keys(self):
        return self._keys

    def add_key(self, key):
        if self._complete:
            raise Exception("account already complete")
        self._keys.append(key)
        self._public_keys.append(key.wallet_key(as_private=False))

    def add_keys(self, keys):
        for key in keys:
            self.add_key(key)

    def set_complete(self):
        if self._complete:
            raise Exception("account already complete")
        self._complete = True

    def leaf_script(self, n, change=False):
        return self.script_for_path("%s/%s" % (n, 1 if change else 0))

    def leaf_payto(self, n, change=False):
        return self.payto_for_path("%s/%s" % (n, 1 if change else 0))

    def address(self, n, change=False):
        return self.leaf_payto(n, change).address(self.netcode)

    def script_for_path(self, path):
        """Get the redeem script for the path.  The multisig format is (n-1) of n, but can be overridden.

        :param: path: the derivation path
        :type: path: str
        :return: the script
        :rtype: ScriptMultisig
        """
        if not self._complete:
            raise Exception("account not complete")
        subkeys = [key.subkey_for_path(path or "") for key in self._keys]
        secs = [key.sec() for key in subkeys]
        if self._sort:
            secs.sort()
        script = ScriptMultisig(self._num_sigs, secs)
        return script

    def payto_for_path(self, path):
        """Get the payto script for the path.  See also :meth:`.script`

        :param: path: the derivation path
        :type: path: str
        :return: the script
        :rtype: LeafPayTo
        """
        script = self.script_for_path(path)
        payto = LeafPayTo(hash160=encoding.hash160(script.script()), path=path)
        return payto


class LeafPayTo(ScriptPayToScript):
    def __init__(self, hash160, path):
        super(LeafPayTo, self).__init__(hash160)
        self.path = path
