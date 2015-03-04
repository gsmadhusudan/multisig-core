from __future__ import print_function
from pycoin.tx import Tx
from pycoin.ecdsa import generator_secp256k1
from pycoin.serialize import b2h, stream_to_bytes
from hierarchy import MultisigAccount, AccountKey
from pycoin.tx.script.tools import *
from pycoin.tx.script import der
import json
import requests
import uuid

__author__ = 'sserrano, devrandom'


class Error(Exception):
    pass


class OracleError(Error):
    pass


class Oracle(object):
    """Keep track of a single Oracle account, including user keys and oracle master public key"""

    def __init__(self, account, tx_db=None, manager=None, base_url=None, num_oracle_keys=1):
        """
        Create an Oracle object

        :param account: multisig account
        :type account: MultisigAccount
        :param tx_db: lookup database for transactions - see pycoin.services.get_tx_db()
        :param manager: the manager identifier for this wallet (only used on creation for now)
        """
        self.account = account
        self.manager = manager
        self.wallet_agent = 'digitaloracle-pycoin-0.01'
        self.tx_db = tx_db
        self.base_url = base_url or 'https://s.digitaloracle.co/'
        self.num_oracle_keys = num_oracle_keys

    def create_oracle_request(self, input_chain_paths, output_chain_paths, spend_id, tx):
        # Have the Oracle sign the tx
        chain_paths = []
        input_scripts = []
        input_txs = []
        for i, inp in enumerate(tx.txs_in):
            input_tx = self.tx_db.get(inp.previous_hash)
            if input_tx is None:
                raise Error("could not look up tx for %s" % (b2h(inp.previous_hash)))
            input_txs.append(input_tx)
            if input_chain_paths[i]:
                redeem_script = self.account.script_for_path(input_chain_paths[i]).script()
                input_scripts.append(redeem_script)
                chain_paths.append(input_chain_paths[i])
                fix_input_script(inp, redeem_script)
            else:
                input_scripts.append(None)
                chain_paths.append(None)
        req = {
            "walletAgent": self.wallet_agent,
            "transaction": {
                "bytes": b2h(stream_to_bytes(tx.stream)),
                "inputScripts": [(b2h(script) if script else None) for script in input_scripts],
                "inputTransactions": [b2h(stream_to_bytes(tx.stream)) for tx in input_txs],
                "chainPaths": chain_paths,
                "outputChainPaths": output_chain_paths,
                "masterKeys": self.account.public_keys[0:-self.num_oracle_keys],
            }
        }
        if spend_id:
            req['spendId'] = spend_id
        return req

    def sign(self, tx, input_chain_paths, output_chain_paths, spend_id=None):
        """
        Have the Oracle sign the transaction

        :param tx: the transaction to be signed
        :type tx: Tx
        :param input_chain_paths: the derivation path for each input, or None if the input does not need to be signed
        :type input_chain_paths: list[str or None]
        :param output_chain_paths: the derivation path for each change output, or None if the output is not change
        :type output_chain_paths: list[str or None]
        :param spend_id: an additional hex ID to disambiguate sends to the same outputs
        :type spend_id: str
        :return: a dictionary with the transaction in 'transaction' if successful
        :rtype: dict
        """
        req = self.create_oracle_request(input_chain_paths, output_chain_paths, spend_id, tx)
        body = json.dumps(req)
        url = self.url() + "/transactions"
        print(body)
        response = requests.post(url, body, headers={'content-type': 'application/json'})
        result = response.json()
        if response.status_code == 200 and result.get('result', None) == 'success':
            if 'transaction' in result:
                tx = Tx.tx_from_hex(result['transaction']['bytes'])
            return {
                'transaction': tx,
                'now': result['now'],
                'spendId': result['spendId'],
                'deferral': result['deferral']
            }
        elif response.status_code == 200 or response.status_code == 400:
            raise OracleError(response.content)
        else:
            raise Error("Unknown response %d" % (response.status_code,))

    def url(self):
        account_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "urn:digitaloracle.co:%s" % (self.account.public_keys[0])))
        url = self.base_url + "keychains/" + account_id
        return url

    def get(self):
        """Retrieve the oracle public key from the Oracle"""
        if self.account.complete:
            raise Exception("the account for this Oracle is already complete")
        url = self.url()
        response = requests.get(url)
        result = response.json()
        if response.status_code == 200 and result.get('result', None) == 'success':
            self.account.add_keys([AccountKey.from_key(s) for s in result['keys']['default']])
            self.num_oracle_keys = len(result['keys']['default'])
            self.account.set_complete()
        elif response.status_code == 200 or response.status_code == 400:
            raise OracleError(response.content)
        else:
            raise Error("Unknown response " + response.status_code)

    def create(self, email=None, phone=None):
        """
        Create an Oracle keychain on server and retrieve the oracle public key

        :param email: the email contact
        :type email: str or unicode
        :param phone: the phone contact
        :type phone: str or unicode
        """
        if self.account.complete:
            raise Exception("account already complete")
        r = {'walletAgent': self.wallet_agent, 'rulesetId': 'default'}
        if self.manager:
            r['managerUsername'] = self.manager
        r['pii'] = {}
        calls = []
        if email:
            r['pii']['email'] = email
            calls.append('email')
        if email:
            r['pii']['phone'] = phone
            calls.append('phone')
        r['parameters'] = {
            "levels": [
                {"asset": "BTC", "period": 60, "value": 0.001},
                {"delay": 0, "calls": calls}
            ]
        }
        r['keys'] = self.account.keys
        body = json.dumps(r)
        url = self.url()
        response = requests.post(url, body, headers={'content-type': 'application/json'})

        result = response.json()
        if response.status_code == 200 and result.get('result', None) == 'success':
            self.account.add_keys([AccountKey.from_key(s) for s in result['keys']['default']])
            self.num_oracle_keys = len(result['keys']['default'])
            self.account.set_complete()
        elif response.status_code == 400 and result.get('error', None) == 'already exists':
            raise OracleError("already exists")
        elif response.status_code == 200 or response.status_code == 400:
            raise OracleError(response.content)
        else:
            raise Error("Unknown response " + response.status_code)


def dummy_signature(sig_type):
    order = generator_secp256k1.order()
    r, s = order - 1, order // 2
    return der.sigencode_der(r, s) + bytes_from_int(sig_type)


def fix_input_script(inp, redeem_script):
    """replace dummy signatures with OP_0 and add redeem script for digitaloracle compatibility"""
    dummy = b2h(dummy_signature(1))
    ops1 = []
    for op in opcode_list(inp.script):
        if op == dummy:
            op = 'OP_0'
        ops1.append(op)
    # FIXME hack to add redeem script omitted by pycoin
    ops1.append(b2h(redeem_script))
    inp.script = compile(' '.join(ops1))
