import time
from enum import Enum

SETTINGS = {
    'BUFFERSIZE': 1024,
    'DISKSIZE': 1024 * 1024 * 100,
    'TIMEOUT': 2.0
}

SERVER_ADDRESS = '127.0.0.1'
PORT = 69


def read(filename):
    try:
        with open(filename, 'rb') as f:
            data = f.read()
        return data
    except:
        return None


def store(filename, data):
    with open(filename, 'wb') as f:
        f.write(data)


def send(sock, addr, data):
    print(f'sending {data} to {addr}')
    sock.sendto(data.package, addr)


def recv(sock):
    data, addr = sock.recvfrom(SETTINGS['BUFFERSIZE'])
    try:
        opcode = data[0:2]
        frmt = opcode_to_package[Operation(opcode)](data)
    except:
        raise IllegalOpCode
    return frmt, addr


def int_to_n_bytes(val, n=2):
    return val.to_bytes(n, 'big')


def int_from_bytes(bytelist):
    return int.from_bytes(bytelist, 'big', signed=False)


class Operation(Enum):
    RRQ = b'\x00\x01'
    WRQ = b'\x00\x02'
    DATA = b'\x00\x03'
    ACK = b'\x00\x04'
    ERROR = b'\x00\x05'


class Mode(Enum):
    NETASCII = 'netascii'
    OCTET = 'octet'
    MAIL = 'mail'

    @staticmethod
    def values():
        return [e.value for e in Mode]


class ErrorCode(Enum):
    NOTDEFINED = b'\x00\x00'
    NOTFOUND = b'\x00\x01'
    ACCESSVIOLATION = b'\x00\x02'
    DISKFULL = b'\x00\x03'
    ILLEGALOP = b'\x00\x04'
    UNKNOWN = b'\x00\x05'
    EXIST = b'\x00\x06'
    NOUSER = b'\x00\x07'


def get_error_msg(code):
    msg = ''
    if code == ErrorCode.NOTDEFINED:
        msg = 'Not defined, see error message (if any).'
    elif code == ErrorCode.NOTFOUND:
        msg = 'File not found.'
    elif code == ErrorCode.ACCESSVIOLATION:
        msg = 'Access violation.'
    elif code == ErrorCode.DISKFULL:
        msg = 'Disk full or allocation exceeded.'
    elif code == ErrorCode.ILLEGALOP:
        msg = 'Illegal TFTP operation.'
    elif code == ErrorCode.UNKNOWN:
        msg = 'Unknown transfer ID.'
    elif code == ErrorCode.EXIST:
        msg = 'File already exists.'
    elif code == ErrorCode.NOUSER:
        msg = 'No such user.'
    return msg


class RRQ:
    def __init__(self, data):
        self.opcode = Operation(data[0:2])
        self.filename = ''
        for byte in data[2::]:
            if byte == 0:
                break
            self.filename += chr(byte)
        mode_data = ''
        for byte in data[2 + len(self.filename) + 1::]:
            if byte == 0:
                break
            mode_data += chr(byte)
        self.mode = Mode(mode_data.lower())

    @staticmethod
    def create(filename, mode):
        return RRQ(
            Operation.RRQ.value
            + filename.encode()
            + b'\x00'
            + mode.encode()
            + b'\x00'
        )

    @property
    def package(self):
        return (
            self.opcode.value
            + self.filename.encode()
            + b'\x00'
            + self.mode.value.encode()
            + b'\x00'
        )

    def __str__(self):
        return f'RRQ [filename={self.filename}]'


class WRQ(RRQ):
    @staticmethod
    def create(filename, mode):
        return WRQ(
            Operation.WRQ.value
            + filename.encode()
            + b'\x00'
            + mode.encode()
            + b'\x00'
        )

    def __str__(self):
        return f'WRQ [filename={self.filename}]'


class DATA:
    def __init__(self, data):
        self.opcode = Operation.DATA
        self.block = int_from_bytes(data[2:4])
        self.data = data[4::]
        if len(self.data) < 512:
            self.last = True
        else:
            self.last = False

    @property
    def package(self):
        return self.opcode.value + int_to_n_bytes(self.block) + self.data

    @staticmethod
    def create(block, data):
        return DATA(
            Operation.DATA.value
            + int_to_n_bytes(block)
            + data
        )

    def __str__(self):
        return f'DATA [block={self.block}, bytes={len(self.data)}]'


class ACK:
    def __init__(self, data):
        self.opcode = Operation.ACK
        self.block = int_from_bytes(data[2:4])

    @staticmethod
    def create(block):
        return ACK(Operation.ACK.value + int_to_n_bytes(block))

    @property
    def package(self):
        return self.opcode.value + int_to_n_bytes(self.block)

    def __str__(self):
        return f'ACK [block={self.block}]'


class ERROR:
    def __init__(self, data):
        self.opcode = Operation.ERROR
        self.code = ErrorCode(data[2:4])
        self.message = ''
        for byte in data[4:]:
            if byte == 0:
                break
            self.message += chr(byte)

    @staticmethod
    def create_from_code(code):
        opcode = Operation.ERROR
        message = get_error_msg(code)
        data = (
            opcode.value
            + code.value
            + message.encode()
            + b'\x00'
        )
        return ERROR(data)

    @property
    def package(self):
        return (
            self.opcode.value
            + self.code.value
            + self.message.encode()
            + b'\x00'
        )

    def __str__(self):
        return f'ERROR <code={self.code}, message={self.message}>'


opcode_to_package = {
    Operation.RRQ: RRQ,
    Operation.WRQ: WRQ,
    Operation.DATA: DATA,
    Operation.ACK: ACK,
    Operation.ERROR: ERROR,
}


class IllegalOpCode(Exception):
    pass
