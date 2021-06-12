#!/usr/bin/env python3

from ctf_gameserver import checkerlib
import random
import logging
import socket

import utils
from treasurehunt.treasurehunt import *


class TemplateChecker(checkerlib.BaseChecker):

    def connect(self):
        logging.info(f"default timeout: {socket.getdefaulttimeout()}")
        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.socket.settimeout(10)
        try:
            logging.info("Connecting ...")
            self.socket.connect((self.ip, 12321, 0, 0))
        except OSError as e:
            logging.error(e)
            return None

        return self.socket

    @staticmethod
    def _get_coords():
        WIDTH = 120
        HEIGHT = 60
        y = random.randrange(HEIGHT)
        x = random.randrange(WIDTH)
        return f"{y},{x}".encode()

    def place_flag(self, tick):
        flag = checkerlib.get_flag(tick).encode()
        logging.info("Placing Flag %s for tick %d" % (flag, tick))

        th = TreasureHunt()
        s = self.connect()
        if not s:
            return checkerlib.CheckResult.DOWN

        th.socketSetup(s)

        # create session
        ret, sess_pub, sess_priv = th.create_session()
        logging.info(f"ret: {ret}")
        if ret:
            return checkerlib.CheckResult.DOWN

        logging.info(f"sess: {sess_pub}/{sess_priv}")

        # open treasure
        coords = self._get_coords()
        logging.info(f"coords: {coords}")
        ret = th.open(coords)
        if ret:
            return checkerlib.CheckResult.FAULTY

        logging.info(f"store: {flag}")
        ret = th.store(flag)
        if ret:
            return checkerlib.CheckResult.FAULTY

        ret = th.close()
        if ret:
            return checkerlib.CheckResult.FAULTY

        checkerlib.store_state(str(tick), [sess_pub, sess_priv, coords])
        checkerlib.set_flagid(sess_pub.decode())

        ret = th.destroy_session()
        if ret:
            return checkerlib.CheckResult.FAULTY

        th.socketTearDown()
        return checkerlib.CheckResult.OK

    def check_service(self):
        th = TreasureHunt()
        s = self.connect()
        if not s:
            return checkerlib.CheckResult.DOWN
        th.socketSetup(s)

        # create session
        ret, sess_pub, sess_priv = th.create_session()
        logging.info(f"ret: {ret}")
        if ret:
            return checkerlib.CheckResult.DOWN

        logging.info(f"sess: {sess_pub}/{sess_priv}")

        # open treasure
        coords = self._get_coords()
        logging.info(f"coords for map check: {coords}")
        ret = th.open(coords)
        if ret:
            return checkerlib.CheckResult.FAULTY
        logging.info(f"opened coords {coords}")

        m = utils.generate_message().encode()
        logging.info(f"storing {m}")
        ret = th.store(m)
        if ret:
            return checkerlib.CheckResult.FAULTY
        logging.info(f"stored {m}")

        logging.info("closing coords")
        ret = th.close()
        if ret:
            return checkerlib.CheckResult.FAULTY
        
        logging.info("opening x")
        ret = th.open(b"x")
        if ret:
            return checkerlib.CheckResult.FAULTY

        logging.info("calling map")
        ret = th.map()
        if ret:
            return checkerlib.CheckResult.FAULTY

        logging.info("checking x for size")
        maplen = th.check()
        if maplen < 60*121:
            logging.info(f"maplen is {maplen}, thats bad.")
            return checkerlib.CheckResult.FAULTY

        logging.info(f"retrieving map with size {maplen}")
        ret, data = th.retrieve(maplen)

        logging.info(f"retrieved {data}")
        if ret:
            return checkerlib.CheckResult.FAULTY

        try:
            lines = data.decode("utf8")
        except ValueError:
            return checkerlib.CheckResult.FAULTY
        lines = lines.strip().split("\n")
        logging.info(f"checking size")
        if len(lines) < 60:
            logging.info(f"invalid height")
            return checkerlib.CheckResult.FAULTY
        for l in lines[60:]:
            if len(l) != 120:
                logging.info(f"invalid width {len(l)}")
                return checkerlib.CheckResult.FAULTY

        logging.info(f"checking map content")
        cy,cx = map(int, coords.decode().split(","))
        bgchars = "#~"
        for y in range(60):
            for x in range(120):
                c = lines[y][x]
                if (x,y) == (cx,cy):
                    if c in bgchars:
                        logging.info(f"found {c} at {y},{x} but expected a mark")
                        return checkerlib.CheckResult.FAULTY
                else:
                    if c not in bgchars:
                        logging.info(f"found {c} at {y},{x} but expected background")
                        return checkerlib.CheckResult.FAULTY

        ret = th.close()
        if ret:
            return checkerlib.CheckResult.FAULTY

        checkerlib.set_flagid(str(sess_pub))

        ret = th.destroy_session()
        if ret:
            return checkerlib.CheckResult.FAULTY

        th.socketTearDown()
        return checkerlib.CheckResult.OK

    def check_flag(self, tick):
        expected_flag = checkerlib.get_flag(tick).encode()
        logging.info("Checking flag %s for tick %d" % (expected_flag, tick))

        data = checkerlib.load_state(str(tick))
        if not data:
            return checkerlib.CheckResult.FLAG_NOT_FOUND

        sess_pub, sess_priv, coords = data

        logging.info(f"sess: {sess_pub}/{sess_priv}")
        logging.info(f"coords: {coords}")

        th = TreasureHunt()
        s = self.connect()
        if not s:
            return checkerlib.CheckResult.DOWN
        th.socketSetup(s)

        # resume session: might not exist cuz place happened when svc was down
        ret = th.resume_session(sess_pub, sess_priv)
        if ret:
            return checkerlib.CheckResult.FLAG_NOT_FOUND

        # open treasure: might not be there cuz place happened when svc was down
        ret = th.open(coords)
        if ret:
            return checkerlib.CheckResult.FLAG_NOT_FOUND

        # retrieve treasure: might not exist cuz place happened when svc was down
        ret, data = th.retrieve(len(expected_flag))
        if ret:
            return checkerlib.CheckResult.FLAG_NOT_FOUND

        logging.info(f"retrieved {data}")
        if expected_flag not in data:
            return checkerlib.CheckResult.FLAG_NOT_FOUND

        ret = th.close()
        if ret:
            return checkerlib.CheckResult.FAULTY

        checkerlib.set_flagid(str(sess_pub))

        ret = th.destroy_session()
        if ret:
            return checkerlib.CheckResult.FAULTY

        th.socketTearDown()
        return checkerlib.CheckResult.OK


if __name__ == '__main__':
    checkerlib.run_check(TemplateChecker)
