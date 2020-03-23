class Artist:
    def __init__(self, name):
        self.name = name


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
    def __init__(self, number, discnum, title):
        self.number = number
        self.discnum = discnum
        self.title = title
