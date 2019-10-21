import mpd as mpd2
import neonmeate.mpd.cache

from gi.repository import GObject, GLib


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

    def stop_playing(self):
        self.client.stop()

    def next_song(self):
        self.client.next()

    def prev_song(self):
        self.client.previous()

    def toggle_pause(self, should_pause):
        if should_pause:
            self.client.pause(1)
        else:
            self.client.play(0)

    def find_artists(self):
        return self.client.list('artist')

    def find_albums(self, artist):
        return self.client.list('album', 'albumartist', artist)

    def status(self):
        return self.client.status()

    def clear_playlist(self):
        self.client.playlistclear()

    def playlistinfo(self):
        return self.client.playlistinfo()

    def populate_cache(self, albumcache):
        artists = self.client.list('artist')
        for artist in artists:
            albums = self.find_albums(artist)
            for album in albums:
                albumcache.add(artist, album)


class MpdState:
    def __init__(self):
        self.state_attrs = {}

    def update(self, attrs):
        self.state_attrs = attrs

    def is_playing(self):
        if 'state' in self.state_attrs:
            return self.state_attrs['state'] == 'play'

    def is_paused(self):
        if 'state' in self.state_attrs:
            return self.state_attrs['state'] == 'pause'

    def playing_status(self):
        return self.state_attrs.get('state', 'stop')

    def elapsed_percent(self):
        if 'elapsed' in self.state_attrs:
            t = float(self.state_attrs['elapsed'])
            d = float(self.state_attrs['duration'])
            return int(100.0 * t / d)
        return 0

    def __str__(self):
        return f'songid={self.song_id}, elapsed={self.elapsed}, duration={self.duration}'


class MpdHeartbeat(GObject.GObject):
    __gsignals__ = {
        'song_played_percent': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
        'song_playing_status': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self, client, millis_interval):
        GObject.GObject.__init__(self)
        self.millis_interval = millis_interval
        self.client = client
        self.source_id = -1
        self.state = MpdState()

    def start(self):
        self.source_id = GLib.timeout_add(self.millis_interval, self.on_sync)

    def stop(self):
        if self.source_id != -1:
            GLib.source_remove(self.source_id)

    def on_sync(self):
        status = self.client.status()
        self.state.update(status)
        self.emit('song_playing_status', self.state.playing_status())
        if self.state.playing_status() == 'stop':
            self.emit('song_played_percent', 0)
        if self.state.is_playing():
            self.emit('song_played_percent', self.state.elapsed_percent())

        return True


if __name__ == '__main__':
    client = Mpd('localhost', 6600)
    client.connect()
    album_cache = neonmeate.mpd.cache.AlbumCache()
    client.populate_cache(album_cache)
    print(album_cache)
