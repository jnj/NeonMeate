import collections
import os


class AlbumCache:
    def __init__(self, root_music_dir):
        self._artists = []
        self._root_music_dir = root_music_dir
        self._albums_by_artist = collections.defaultdict(dict)

    def add(self, artist, album, songs):
        if artist not in self._albums_by_artist:
            self._artists.append(artist)
        self._albums_by_artist[artist][album] = songs

    def cover_art_path(self, artist, album):
        albums = self._albums_by_artist[artist]
        if album in albums:
            songs = albums[album]
            if songs:
                song_path = songs[0]['file']
                return os.path.join(self._root_music_dir, os.path.dirname(song_path), 'cover.jpg')
        return None

    def all_artists_and_albums(self):
        for artist in self._artists:
            albums = sorted(self.get_albums(artist))
            for album in albums:
                yield artist, album

    def all_artists(self):
        return self._artists

    def get_albums(self, artist):
        return self._albums_by_artist[artist]

    def __str__(self):
        return str(self._artists)
