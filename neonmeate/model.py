def get_sanitized_string(dictlike, key):
    val = None
    if key in dictlike:
        val = dictlike[key]
        val = val.strip()
    return None if not val else val


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


class Album:

    @staticmethod
    def sorted_chrono(albums):
        return sorted(albums, key=lambda album: (album.date, album.title, album.artist))

    def __init__(self, artist, title, date, songs, dirpath):
        self.date = date
        self.songs = songs
        self.artist = artist
        self.title = title
        self.dirpath = dirpath

    def __str__(self):
        return f'Album:title={self.title}, date={self.date}, artist={self.artist}'

    def sorted_songs(self):
        return sorted(self.songs, key=lambda song: (song.discnum, song.number))


class Song:
    def __init__(self, number, discnum, title, file):
        self.number = number
        self.discnum = discnum
        self.title = title
        self.file = file
