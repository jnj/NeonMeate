from mpd import MPDClient


class Mpd:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        c = MPDClient()
        c.timeout = 10
        c.idletimeout = None
        self.client = c

    def connect(self):
        self.client.connect(self.host, self.port)

    def close(self):
        self.client.close()
        self.client.disconnect()

    def find_artists(self):
        return self.client.list('artist')
