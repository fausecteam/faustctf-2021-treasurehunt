import unittest
import logging
from treasurehunt.treasurehunt import *


class TestTreasureHunt(unittest.TestCase):

    def setUp(self):
        self.th = TreasureHunt()
        self.th.procSetup()
        ret, sess_pub, sess_priv = self.th.create_session()
        assert ret == 0, "create_session() returned non-zero status"

        self.sess_pub = sess_pub
        self.sess_priv = sess_priv

    def tearDown(self):
        self.th.destroy_session()
        self.th.procTearDown()

    def test_create_destroy_session(self):
        pass

    def test_store_retrieve(self):
        ret = self.th.open(b"test")
        assert 0 == ret, "open failed"

        treasure = b"foobar"
        ret = self.th.store(treasure)
        assert 0 == ret, "store failed"

        ret, data = self.th.retrieve(len(treasure))
        assert 0 == ret, "retrieve failed"
        assert treasure == data, "retrieved treasure incorrect"

        ret = self.th.close()
        assert 0 == ret, "close failed"

    def test_resume(self):
        ret = self.th.open(b"test1")
        assert 0 == ret, "open failed"

        treasure = b"foobar"
        ret = self.th.store(treasure)
        assert 0 == ret, "store failed"

        ret, data = self.th.retrieve(len(treasure))
        assert 0 == ret, "retrieve failed"
        assert treasure in data, "retrieving treasure failed"

        ret = self.th.close()
        assert 0 == ret, "close failed"

        ret = self.th.destroy_session()
        assert 0 == ret, "destroy session failed"

        # setUp saves theh pub and private part from prev session
        ret = self.th.resume_session(self.sess_pub, self.sess_priv)
        assert 0 == ret, "resume session failed"

        ret = self.th.open(b"test2")
        assert 0 == ret, "open failed"

        treasure = b"barfoo"
        ret = self.th.store(treasure)
        assert 0 == ret, "store failed"

        ret, data = self.th.retrieve(len(treasure))
        assert 0 == ret, "retrieve failed"
        assert treasure in data, "retrieving treasure failed"

        ret = self.th.close()
        assert 0 == ret, "close failed"


if __name__ == '__main__':
    unittest.main()

