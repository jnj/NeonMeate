import collections
import os


def resolve_art(directory):
    for basename in ['cover', 'folder', 'artwork']:
        for extension in ['jpg', 'jpeg', 'png', 'gif']:
            path = os.path.join(directory, f'{basename}.{extension}')
            if os.path.exists(path):
                return path
    return None


class AlbumCache:
    def __init__(self, root_music_dir):
        self._artists = []
        self._root_music_dir = root_music_dir
        self._albums_by_artist = collections.defaultdict(dict)

    def add(self, artist, album, songs):
        if artist not in self._albums_by_artist:
            self._artists.append(artist)
        albums = self._albums_by_artist[artist]
        if album not in albums:
            year = int(songs[0]['date'])
            albums[album] = AlbumInfo(artist, album, year, songs)

    def cover_art_path(self, artist, album):
        # TODO Pass in date as well
        # TODO Resolve png, etc.
        albums = self._albums_by_artist[artist]
        if album in albums:
            albuminfo = albums[album]
            if albuminfo.art_path is not None:
                return albuminfo.art_path
            songs = albuminfo.songs
            if songs:
                song_path = songs[0]['file']
                artpath = resolve_art(os.path.join(self._root_music_dir, os.path.dirname(song_path)))
                if artpath is not None:
                    albuminfo.art_path = artpath
                return artpath
        return None

    def all_artists_and_albums(self):
        for artist in self._artists:
            albums = sorted(self.get_albums(artist))
            for album in albums:
                yield artist, album.title

    def all_artists(self):
        return self._artists

    def get_albums(self, artist):
        return self._albums_by_artist[artist]

    def __str__(self):
        return str(self._artists)


class AlbumInfo:
    def __init__(self, artist, title, year, songs):
        self.title = title
        self.artist = artist
        self.year = year
        self.songs = songs
        self.art_path = None
