import socket
from threading import Thread
import time
import utils

clients = {}


class Client:

    def __init__(self, server_socket, address):
        self.socket = server_socket
        self.data_block = b''
        self.data_file = None
        self.address = address
        self.filename = ''
        self.file = None
        self.file_to_client = None
        self.block = 0
        self.package = None
        self.last_package = None
        self.deadline = 0
        self.counter_timeout = 0

    def read(self):
        self.filename = self.data_file.filename
        if (data_ := utils.read(self.data_file.filename)) is None:
            error = utils.ERROR.create_from_code(utils.ErrorCode.NOTFOUND)
            utils.send(self.socket, self.address, error)
            del clients[self.address]
            return

        self.data_block = data_
        self.block = 0
        self.package = utils.DATA.create(1, data_[0:512])
        self.last_package = self.package
        utils.send(self.socket, self.address, self.package)

    def write(self):
        filename = self.data_file.filename
        if (data_ := utils.read(filename)) is not None:
            error = utils.ERROR.create_from_code(utils.ErrorCode.EXIST)
            utils.send(self.socket, self.address, error)
            del clients[self.address]
            return
        self.filename = filename
        utils.send(self.socket, self.address, utils.ACK.create(0))

    def data(self):
        self.package = utils.ACK.create(self.data_file.block)
        self.last_package = self.package
        utils.send(self.socket, self.address, self.package)
        self.data_block += self.data_file.data

        if self.data_file.last:
            utils.store(self.filename, self.data_block)
            print(f'File {self.filename} with {len(self.data_block)} bytes stored')
            del clients[self.address]
            return

    def ack(self):
        self.block = self.data_file.block
        file = self.data_block[self.block * 512:self.block * 512 + 512]
        self.package = utils.DATA.create(self.block + 1, file)
        self.last_package = self.package
        utils.send(self.socket, self.address, self.package)
        if len(file) < 512:
            print(f'File {self.filename} with {len(self.data_block)} bytes send')
            del clients[self.address]
            return

    def get_opcode(self, opcode):
        if opcode == utils.Operation.RRQ:
            self.read()
        elif opcode == utils.Operation.WRQ:
            self.write()
        elif opcode == utils.Operation.DATA:
            self.data()
        elif opcode == utils.Operation.ACK and self.data:
            self.ack()

    def check_timeout(self):
        if time.time() >= self.deadline:
            if self.counter_timeout < 10:
                print('Таймаут ', self.address)
                utils.send(self.socket, self.address, self.package)
            else:
                print('Превышен предел таймаутов')
                del clients[self.address]
                return


class ServerThread(Thread):

    def __init__(self, server_socket: socket):
        Thread.__init__(self)
        self.socket = server_socket

    def run(self):
        while True:
            try:
                data, address = utils.recv(self.socket)
            except socket.timeout:
                for client in clients:
                    client.check_timeout()
            else:
                if address not in clients.keys():
                    clients[address] = Client(self.socket, address)
                clients[address].data_file = data
                clients[address].deadline = time.time() + utils.SETTINGS['TIMEOUT']
                clients[address].counter_timeout = 0
                clients[address].get_opcode(data.opcode)

                for client in clients:
                    client.check_timeout()


def main():
    print('RUN')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((utils.SERVER_ADDRESS, utils.PORT))
    sock.settimeout(utils.SETTINGS['TIMEOUT'])
    main_thread = ServerThread(sock)
    main_thread.start()
    while True:
        if input() == 'exit':
            sock.close()
            print('Exit...')
            exit()


main()
