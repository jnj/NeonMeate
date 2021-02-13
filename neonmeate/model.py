class Artist:

    @staticmethod
    def sanitize_artist_name(name):
        if name is None:
            name = ''
        else:
            name = name.strip()
        if name == '':
            name = '<Unknown>'
        return name

    def __init__(self, name):
        if isinstance(name, dict):
            d = name
            for key in ['artist', 'name']:
                if key in d:
                    name = d[key]
                    break
        self.name = Artist.sanitize_artist_name(name)


class Album:

    @staticmethod
    def sorted_chrono(albums):
        return sorted(albums, key=lambda album: album.date)

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
