import serial

class CommandConnection:
    def __init__(self, verbose: bool = False):
        self.conn = None
        self.verbose = verbose

    def open_port(self, port):
        self.conn = serial.Serial(port, baudrate=57600, timeout=1)

    def debug_print(self, farg, *fargs):
        if self.verbose:
            print(farg, *fargs)

    def send_cmd(self, str):
        str += '\r\n'
        data = bytes(str, 'utf-8')
        self.debug_print('> ', data)
        self.conn.write(data)

    def recv_cmd(self) -> str:
        data = self.conn.readline() # NOTE readline uses sole \n as a line separator
        if data:
            self.debug_print('< ', data)
            str = data.decode().strip('\r\n ')
            return str
        return None
