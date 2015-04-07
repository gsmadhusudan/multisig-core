__author__ = 'devrandom'

class BatchService(object):
    """Marker class for providers that implement spendables_for_addresses"""
    def spendables_for_addresses(self, addresses):
        """
        :param list[str] addresses:
        :rtype: dict[str, list[pycoin.tx.Spendable]]
        """
        raise NotImplementedError()