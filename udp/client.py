import socket
import utils

SETTINGS = {
    'MODE': utils.Mode.OCTET,
    'CONNECT': ('127.0.0.1', 69),
}


def loop(sock):
    while True:
        try:
            inp = input('> ').lower().split(' ')
        except:
            break
        if inp[0] == 'get':
            get(sock, inp[1:])
        elif inp[0] == 'put':
            put(sock, inp[1:])


def put(sock, filenames):
    client_block = 0
    timeout_counter = 0
    for filename in filenames:
        file = utils.read(filename)
        if file is None:
            print(f'File {filename} does not exists')
            continue

        wrq = utils.WRQ.create(filename, SETTINGS['MODE'].value)
        print(f'sending {wrq}')
        sock.sendto(wrq.package, SETTINGS['CONNECT'])
        file_block = file[0:512]
        block = 0

        while True:
            try:
                data, address = utils.recv(sock)
            except socket.timeout:
                if timeout_counter > 10:
                    print('Timed out')
                    break
                else:
                    print('Retrying...')
                    sock.sendto(wrq.package, SETTINGS['CONNECT'])
                    timeout_counter += 1

            print(f'recieved {data}')
            if data.opcode == utils.Operation.ERROR:
                break

            elif data.opcode == utils.Operation.ACK:
                block = data.block

                if client_block == block:
                    client_block += 1

                data_pack = utils.DATA.create(client_block, file_block)
                if len(data_pack.data) == 0:
                    break
                print(f'sending {data_pack}')
                sock.sendto(data_pack.package, address)

                file_block = file[client_block * 512: client_block * 512 + 512]


def get(sock, filenames):
    client_block = 1
    timeout_counter = 0

    for filename in filenames:
        if utils.read(filename) is not None:
            print(f'File {filename} already exist')
            continue
        rrq = utils.RRQ.create(filename, SETTINGS['MODE'].value)
        print(f'sending {rrq}')
        sock.sendto(rrq.package, SETTINGS['CONNECT'])
        file = b''
        last = False

        while not last:
            try:
                data, address = utils.recv(sock)
            except socket.timeout:
                if timeout_counter > 10:
                    print('Timed out')
                    break
                else:
                    print('Retrying...')
                    sock.sendto(rrq.package, SETTINGS['CONNECT'])
                    timeout_counter += 1
            else:
                print(f'recieved {data}')
                if data.opcode == utils.Operation.ERROR:
                    last = False
                    break

                if data.opcode == utils.Operation.DATA:
                    last = data.last

                    if client_block == data.block:
                        file += data.data
                        if len(data.data) < 512:
                            print('File accepted') 
                            break
                        else:
                            ack = utils.ACK.create(data.block)
                            print(f'sending {ack}')
                            sock.sendto(ack.package, address)

                            client_block += 1

        if last:
            utils.store(filename, file)
            break


def init():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return sock


loop(init())
