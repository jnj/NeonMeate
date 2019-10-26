from concurrent import futures

import mpd as mpd2
from gi.repository import GObject, GLib

import neonmeate.mpd.cache
import neonmeate.nmasync as nmasync


class Mpd:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._client = mpd2.MPDClient()
        #self._hb_client = mpd2.MPDClient()
        self._client.timeout = 10
        self._client.idletimeout = None
        self._status = {}

    def connect(self):
        """
        Connects to the MPD server, blocking until the server
        status is obtained.
        """
        self._client.connect(self._host, self._port)
        self._status = self.status()

    def close(self):
        self._client.close()
        self._client.disconnect()

    def idle(self):
        while True:
            changed = self._client.idle()
            print(changed)

    def stop_playing(self):
        self._client.send_stop()

    def next_song(self):
        self._client.send_next()

    def prev_song(self):
        self._client.send_previous()

    def toggle_pause(self, should_pause):
        mpdstatus = self.status()
        if should_pause:
            self._client.send_pause(1)
        else:
            if 'state' in mpdstatus and mpdstatus['state'] == 'pause':
                self._client.send_pause(0)
            else:
                self._client.send_play(0)

    def find_artists(self):
        return self._client.list('artist')

    def find_albums(self, artist):
        return self._client.list('album', 'albumartist', artist)

    def status(self):
        return self._client.status()

    def clear_playlist(self):
        self._client.send_playlistclear()

    def playlistinfo(self):
        return self._client.playlistinfo()

    def populate_cache(self, albumcache):
        artists = self._client.list('artist')
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
            return 100.0 * t / d
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
        self._thread = None

    def start(self):
        # self.source_id = GLib.timeout_add(self.millis_interval, self.on_sync)
        self._thread = nmasync.PeriodicTask(500, self._on_delay)
        self._thread.start()

    def stop(self):
        self._thread.stop()

    def _on_delay(self):
        print("checking status....")
        status = self.client.status()
        print(status)
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
    client.idle()
    # album_cache = neonmeate.mpd.cache.AlbumCache()
    # client.populate_cache(album_cache)
    # print(album_cache)
