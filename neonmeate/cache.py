class AlbumCache:
    def __init__(self):
        self.artists = {}

    def add(self, artist, album):
        if artist not in self.artists:
            self.artists[artist] = {}
        a = self.artists[artist]
        a[album] = 1

    def all_artists(self):
        return self.artists.keys()

    def get_albums(self, artist):
        return list(self.artists.get(artist).keys())

    def __str__(self):
        return str(self.artists)
