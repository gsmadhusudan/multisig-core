from unittest import TestCase
from pycoin.serialize import h2b
from multisigcore.hierarchy import MasterKey
from tests import *

__author__ = 'devrandom'

class HierarchyTest(TestCase):
    def setUp(self):
        self.master_key = MasterKey.from_seed(h2b("000102030405060708090a0b0c0d0e0f"))
        self.master_key1 = MasterKey.from_seed(h2b("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542"))
        self.multisig_account = make_multisig_account()

    def test_master(self):
        self.assertEqual(self.master_key.as_text(), "xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8")
        self.assertEqual(self.master_key.as_text(as_private=True), "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi")
        self.assertEqual(self.master_key1.as_text(), "xpub661MyMwAqRbcFW31YEwpkMuc5THy2PSt5bDMsktWQcFF8syAmRUapSCGu8ED9W6oDMSgv6Zz8idoc4a6mr8BDzTJY47LJhkJ8UB7WEGuduB")
        self.assertEqual(self.master_key1.as_text(as_private=True), "xprv9s21ZrQH143K31xYSDQpPDxsXRTUcvj2iNHm5NUtrGiGG5e2DtALGdso3pGz6ssrdK4PFmM8NSpSBHNqPqm55Qn3LqFtT2emdEXVYsCzC2U")

    def test_account(self):
        account = self.master_key.account_for_path("0H/1/2H")
        self.assertEqual(account.as_text(), "xpub6D4BDPcP2GT577Vvch3R8wDkScZWzQzMMUm3PWbmWvVJrZwQY4VUNgqFJPMM3No2dFDFGTsxxpG5uJh7n7epu4trkrX7x7DogT5Uv6fcLW5")
        self.assertEqual(account.as_text(as_private=True), "xprv9z4pot5VBttmtdRTWfWQmoH1taj2axGVzFqSb8C9xaxKymcFzXBDptWmT7FwuEzG3ryjH4ktypQSAewRiNMjANTtpgP4mLTj34bhnZX7UiM")
        leaf = account.leaf_for_path("2/1000000000")
        self.assertEqual(leaf.as_text(), "xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy")
        self.assertEqual(leaf.as_text(as_private=True), "xprvA41z7zogVVwxVSgdKUHDy1SKmdb533PjDz7J6N6mV6uS3ze1ai8FHa8kmHScGpWmj4WggLyQjgPie1rFSruoUihUZREPSL39UNdE3BBDu76")

    def test_electrum(self):
        # Electrum seed v6: fade really needle dinner excuse half rabbit sorry stomach confusion bid twice suffer
        m = MasterKey.from_seed(h2b("7043e6911790bbcc5d0c5c00ab4c3deb2641af606f987113bcc28b7ccd94b2b6be3a0203be1c61fe64e6d6e4e806107fec9e80d5bf9a62284d3bb45550d797f0"))
        a = m.electrum_account(0)
        l = a.leaf(0)
        self.assertEqual(l.address(), "1AGWXxRe7FwWJJ6k5uAfwcoA7Sov9AYNVK")

    def test_multisig_payto(self):
        payto = self.multisig_account.payto_for_path(TEST_PATH)
        self.assertEqual("34DjTcNWGReJV4xx7R1AWK7FTz3xMwMcjA", payto.address())

