import os
import subprocess
import colorama
from colorama import Fore, Style
import struct

from ctypes import *


DIR = os.path.dirname(os.path.abspath(__file__))
DATADIR = os.path.join(DIR, "data")
EXEC_PATH = os.path.join(DIR, "../src/treasurehunt")


p8 = lambda val: struct.pack("<B", val)
p32 = lambda val: struct.pack("<I", val)
p64 = lambda val: struct.pack("<Q", val)
u64 = lambda data: struct.unpack("<Q", data)[0]


class ParamType():
    NONE = 0
    VALUE_INPUT = 1
    VALUE_OUTPUT = 2
    VALUE_INOUT = 3
    MEMREF_INPUT = 5
    MEMREF_OUTPUT = 6
    MEMREF_INOUT = 7


class Value(Structure):
    _fields_ = [("a", c_ulonglong),  ("b", c_ulonglong)]

    def __str__(self):
        out = ""
        out += f"value.a: {self.a}\n"
        out += f"value.b: {self.b}\n"
        return out


class Memref(Structure):
    _fields_ = [("off", c_ulonglong),  ("sz", c_ulonglong)]


class Param(Union):
    _fields_ = [("value", Value), ("memref", Memref)]


class Ctx(Structure):
    _pack_ = 1
    _fields_ = [("sessCmdId", c_ushort), ("cmdId", c_ushort), 
            ("paramTypes", c_ushort), ("params", Param * 2)]

    def __str__(self):
        out = ""
        out += f"sessCmdId: {self.sessCmdId}\n"
        out += f"cmdId: {self.cmdId}\n"
        out += "paramTypes: {:#x}\n".format(self.paramTypes)
        out += f"{self.params[0]}\n"
        out += f"{self.params[1]}\n"
        return out


class CMD:
    OPEN = 1337
    STORE = 1338
    RETRIEVE = 1339
    MAP = 1340
    CHECK = 1341
    CLOSE = 1342


class SESSCMD:
    SESSOPEN = 1
    INVOKE = 2
    SESSCLOSE = 3


def print_err(msg):
    print(f"{Fore.RED}{msg}{Style.RESET_ALL}")


def print_info(msg):
    print(f"{Fore.BLUE}{msg}{Style.RESET_ALL}")


class TreasureHunt():

    def procSetup(self):
        os.chdir(os.path.dirname(EXEC_PATH))
        self.proc = subprocess.Popen(f"./{os.path.basename(EXEC_PATH)}",
                stdout=subprocess.PIPE,
                stdin=subprocess.PIPE,
                bufsize=0)
        self.wfile = self.proc.stdin
        self.rfile = self.proc.stdout

    def procTearDown(self):
        self.proc.stdout.close()
        self.proc.stdin.close()
        self.proc.terminate()
        self.proc.wait(3)

    def socketSetup(self, s):
        self.wfile = s.makefile('wb', buffering=0)
        self.rfile = s.makefile('rb')
        self.socket = s

    def socketTearDown(self):
        self.wfile.close()
        self.rfile.close()
        self.socket.close()

    def _readn(self, n):
        outs = b""
        while len(outs) != n:
            r = self.rfile.read(n - len(outs))
            if not r:
                return None
            outs += r
        return outs

    def create_session(self):
        """ create a session

        Args:
            None

        Returns:
            int: return code, 0 if successful
            bytes: public part of the session id, if ret is 0
            bytes: public part of the session id, if ret is 0

        """
        BUFSZ = 256
        sessCmdId = c_ushort(SESSCMD.SESSOPEN)
        cmdId = c_ushort(0)  # not needed
        paramTypes = c_ushort(ParamType.MEMREF_OUTPUT | ParamType.VALUE_OUTPUT << 4)

        param0 = Param(memref=Memref(c_ulonglong(0x0), c_ulonglong(BUFSZ)))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            outs = self._readn(sizeof(ctx) + BUFSZ)
            if not outs:
                return -1, None, None
        except:
            return -1, None, None

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))

        data = outs[sizeof(ctx):BUFSZ]
        session_pub = data[:11]
        session_priv = data[12:12+31]

        return rparam1.a, session_pub, session_priv

    def resume_session(self, sess_pub, sess_priv):
        """ resume a session

        Args:
            sess_pub (bytes): public part of the session id
            sess_priv (bytes): private part of the session id

        Returns:
            int: return code, 0 if successful
        """
        BUFSZ = 256
        buf = sess_pub + b"\x00"
        buf += sess_priv + b"\x00"
        buf = buf.ljust(BUFSZ, b"\x00")

        sessCmdId = c_ushort(SESSCMD.SESSOPEN)
        cmdId = c_ushort(0)  # not needed
        paramTypes = c_ushort(ParamType.MEMREF_INPUT | ParamType.VALUE_OUTPUT << 4)

        param0 = Param(memref=Memref(c_ulonglong(0x0), c_ulonglong(BUFSZ)))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            self.wfile.write(buf)
            outs = self._readn(sizeof(ctx))
            if not outs:
                return -1
        except:
            return -1

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))
        return rparam1.a


    def destroy_session(self):
        """ destroy the session

        Args:
            None

        Returns:
            int: return code, 0 if successful
        """
        sessCmdId = c_ushort(SESSCMD.SESSCLOSE)
        cmdId = c_ushort(0)  # not needed
        paramTypes = c_ushort(ParamType.VALUE_OUTPUT)

        param0 = Param(Value(0,0))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            outs = self._readn(sizeof(ctx))
            if not outs:
                return -1
        except:
            return -1

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))
        return rparam0.a

    def open(self, fname):
        """ open treasure

        Args:
            fname (bytes): filename of the treasure

        Returns:
            int: return code, 0 if successful
        """
        BUFSZ = 256
        sessCmdId = c_ushort(SESSCMD.INVOKE)
        cmdId = c_ushort(CMD.OPEN)
        paramTypes = c_ushort(ParamType.MEMREF_INPUT | ParamType.VALUE_OUTPUT << 4)

        param0 = Param(memref=Memref(c_ulonglong(0x0), c_ulonglong(BUFSZ)))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            self.wfile.write(fname.ljust(BUFSZ, b"\x00"))
            outs = self._readn(sizeof(ctx))
            if not outs:
                return -1
        except:
            return -1

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))
        return rparam1.a

    def close(self):
        """ close treasure

        Args:
            None

        Returns:
            int: return code, 0 if successful
        """
        sessCmdId = c_ushort(SESSCMD.INVOKE)
        cmdId = c_ushort(CMD.CLOSE)  # not needed
        paramTypes = c_ushort(ParamType.VALUE_OUTPUT | ParamType.NONE << 4)

        param0 = Param(Value(0,0))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            outs = self._readn(sizeof(ctx))
            if not outs:
                return -1
        except:
            return -1

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))

        return rparam0.a

    def check(self):
        """ close treasure

        Args:
            None

        Returns:
            int: return code, 0 if successful
        """
        sessCmdId = c_ushort(SESSCMD.INVOKE)
        cmdId = c_ushort(CMD.CHECK)
        paramTypes = c_ushort(ParamType.VALUE_OUTPUT | ParamType.NONE << 4)

        param0 = Param(Value(0,0))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            outs = self._readn(sizeof(ctx))
            if not outs:
                return -1
        except:
            return -1

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))

        return rparam0.a

    def store(self, data):
        """ store treasure

        Args:
            data (bytes): data to be stored in treasure

        Returns:
            int: return code, 0 if successful
        """
        BUFSZ = len(data)
        sessCmdId = c_ushort(SESSCMD.INVOKE)
        cmdId = c_ushort(CMD.STORE)
        paramTypes = c_ushort(ParamType.MEMREF_INPUT | ParamType.VALUE_OUTPUT << 4)

        param0 = Param(memref=Memref(c_ulonglong(0x0), c_ulonglong(BUFSZ)))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            self.wfile.write(data)
            outs = self._readn(sizeof(ctx))
            if not outs:
                return -1
        except:
            return -1

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))
        return rparam1.a

    def retrieve(self, sz):
        """ store treasure

        Args:
            sz (bytes): size of the treasure to be retrieved

        Returns:
            int: return code, 0 if successful
            bytes: the treasure
        """
        sessCmdId = c_ushort(SESSCMD.INVOKE)
        cmdId = c_ushort(CMD.RETRIEVE)
        paramTypes = c_ushort(ParamType.MEMREF_OUTPUT | ParamType.VALUE_OUTPUT << 4)

        param0 = Param(memref=Memref(c_ulonglong(0x0), c_ulonglong(sz)))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            outs = self._readn(sizeof(ctx) + sz)
            if not outs:
                return -1, None
        except:
            return -1, None

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))

        data = outs[sizeof(ctx):]
        return rparam1.a, data

    def map(self):
        """ store treasure map

        Args:
            None

        Returns:
            int: return code, 0 if successful
        """
        sessCmdId = c_ushort(SESSCMD.INVOKE)
        cmdId = c_ushort(CMD.MAP)
        paramTypes = c_ushort(ParamType.VALUE_OUTPUT | ParamType.NONE << 4)

        param0 = Param(Value(0,0))
        param1 = Param(Value(0,0))
        ctx = Ctx(sessCmdId, cmdId, paramTypes, (param0, param1))

        try:
            ins = string_at(pointer(ctx), sizeof(ctx))
            self.wfile.write(ins)
            outs = self._readn(sizeof(ctx))
            if not outs:
                return -1
        except:
            return -1

        # get header
        header = outs[:sizeof(ctx)]
        rsessCmdId, rcmdId, rparamTypes, rparam0Off, rparam0Sz, rparam1Off, rparam1Sz = struct.unpack("<HHHQQQQ", header)
        rparam0 = Value(rparam0Off, rparam0Sz)
        rparam1 = Value(rparam1Off, rparam1Sz)
        rctx = Ctx(rsessCmdId, rcmdId, rparamTypes, (Param(rparam0), Param(rparam1)))

        return rparam0.a
