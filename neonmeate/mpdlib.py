import mpd as mpd2
import neonmeate.cache


class Mpd:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        c = mpd2.MPDClient()
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

    def find_albums(self, artist):
        return self.client.list('album', 'albumartist', artist)

    def status(self):
        return self.client.status()

    def populate_cache(self, albumcache):
        artists = self.client.list('artist')
        for artist in artists:
            albums = self.find_albums(artist)
            for album in albums:
                albumcache.add(artist, album)


if __name__ == '__main__':
    client = Mpd('localhost', 6600)
    client.connect()
    album_cache = neonmeate.cache.AlbumCache()
    client.populate_cache(album_cache)
    print(album_cache)
