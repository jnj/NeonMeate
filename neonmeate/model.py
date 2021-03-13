import functools


def get_sanitized_string(dictlike, key):
    val = None
    if key in dictlike:
        val = dictlike[key]
        val = val.strip()
    return None if not val else val


@functools.total_ordering
class Artist:
    NameKeys = ['albumartist', 'artist', 'name']

    @staticmethod
    def create(dictlike):
        k = ''
        if isinstance(dictlike, dict):
            for k in Artist.NameKeys:
                name = get_sanitized_string(dictlike, k)
                if name:
                    return Artist(name, k == 'albumartist')
        return None

    def __init__(self, name, is_albumartist):
        self.is_albumartist = is_albumartist
        self.name = name

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return self.name

    def __eq__(self, other):
        return isinstance(other, Artist) and other.name == self.name

    def __hash__(self):
        return hash(self.name)


class Album:

    @staticmethod
    def chrono_sort_key(album):
        return album.date, album.title, album.artist

    @staticmethod
    def sorted_chrono(albums):
        return sorted(albums, key=Album.chrono_sort_key)

    def __init__(self, artist, title, date, songs, dirpath):
        self.date = date
        self.songs = songs
        self.artist = artist
        self.title = title
        self.dirpath = dirpath

    def __str__(self):
        return f'Album:title={self.title}, ' \
               f'date={self.date}, ' \
               f'artist={self.artist}'

    def __eq__(self, other):
        return isinstance(other, Album) and other.dirpath == self.dirpath

    def __hash__(self):
        return hash(self.dirpath)

    def sorted_songs(self):
        return sorted(self.songs, key=Song.sort_key)


class Song:

    @staticmethod
    def sort_key(song):
        discnumkey = song.discnum or 1
        return discnumkey, song.number

    @staticmethod
    def create(mpd_song_item):
        return Song(
            int(mpd_song_item['track']),
            int(mpd_song_item.get('disc', 1)),
            mpd_song_item['title'],
            mpd_song_item['file'],
            mpd_song_item['artist'],
            mpd_song_item.get('albumartist', None)
        )

    def __init__(self, number, discnum, title, file, artist=None,
                 albumartist=None):
        """
        Creates a Song instance. The artist should only by non-None
        if this song is part of a compilation album.
        """
        self.number = number
        self.discnum = discnum
        self.title = title
        if isinstance(self.title, list):
            self.title = self.title[0]
        self.file = file
        self.artist = artist
        self.albumartist = albumartist

    def is_compilation_track(self):
        return self.artist != self.albumartist and self.albumartist is not None

    def __hash__(self):
        return hash(self.file)

    def __eq__(self, other):
        return isinstance(other, Song) and other.file == self.file

    def __str__(self):
        return f'Song:number={self.number}, ' \
               f'discnum={self.discnum}, ' \
               f'title={self.title}, ' \
               f'artist={self.artist}, ' \
               f'file={self.file}'
