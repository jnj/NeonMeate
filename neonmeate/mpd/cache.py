import collections


class AlbumCache:
    def __init__(self):
        self.artists = []
        self.albums_by_artist = collections.defaultdict(list)

    def add(self, artist, album):
        if artist not in self.albums_by_artist:
            self.artists.append(artist)
        self.albums_by_artist[artist].append(album)

    def all_artists_and_albums(self):
        for artist in self.artists:
            albums = sorted(self.get_albums(artist))
            for album in albums:
                yield artist, album

    def all_artists(self):
        return self.artists

    def get_albums(self, artist):
        return self.albums_by_artist[artist]

    def __str__(self):
        return str(self.artists)
