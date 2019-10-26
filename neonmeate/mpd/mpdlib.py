import mpd as mpd2
from gi.repository import GObject

import neonmeate.mpd.cache
import neonmeate.nmasync as nmasync


class Mpd:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._client = mpd2.MPDClient()
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

    def currentsong(self):
        return self._client.currentsong()

    def idle(self):
        while True:
            changed = self._client.idle()
            print(changed)

    def stop_playing(self):
        nmasync.RunAsync(self._client.stop)

    def next_song(self):
        nmasync.RunAsync(self._client.next)

    def prev_song(self):
        nmasync.RunAsync(self._client.previous)

    def toggle_pause(self, should_pause):
        mpdstatus = self.status()
        if should_pause:
            nmasync.RunAsync(lambda: self._client.pause(1))
        else:
            if 'state' in mpdstatus and mpdstatus['state'] == 'pause':
                nmasync.RunAsync(lambda: self._client.pause(0))
            else:
                nmasync.RunAsync(lambda: self._client.play(0))

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


class MpdHeartbeat(GObject.GObject):
    __gsignals__ = {
        'song_played_percent': (GObject.SignalFlags.RUN_FIRST, None, (float,)),
        'song_playing_status': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'song_changed': (GObject.SignalFlags.RUN_FIRST, None, (str, str))
    }

    def __init__(self, client, millis_interval):
        GObject.GObject.__init__(self)
        self._client = client
        self._thread = nmasync.PeriodicTask(millis_interval, self._on_hb_interval)
        self._mpd_status = {}
        self._song_id = '-1'

    def start(self):
        self._thread.start()

    def stop(self):
        self._thread.stop()

    def _on_hb_interval(self):
        self._mpd_status = self._client.status()
        play_status = self._mpd_status.get('state', 'stop')
        self.emit('song_playing_status', play_status)
        self._check_song_changed()

        if play_status == 'stop':
            self.emit('song_played_percent', 0)

        if play_status == 'play':
            self.emit('song_played_percent', self._elapsed_percent())

        return True

    def _check_song_changed(self):
        song_id = self._mpd_status.get('songid', '-1')
        if song_id != self._song_id:
            song_info = self._client.currentsong()
            self.emit('song_changed', song_info['artist'], song_info['title'])

    def _mpd_state(self):
        return self._mpd_status.get('state', 'unknown')

    def _state_is(self, state_value):
        return self._mpd_state() == state_value

    def _is_playing(self):
        return self._state_is('play')

    def _is_paused(self):
        return self._state_is('pause')

    def _elapsed_percent(self):
        t = float(self._mpd_status.get('elapsed', 0))
        d = float(self._mpd_status.get('duration', 1))
        return t / d


if __name__ == '__main__':
    client = Mpd('localhost', 6600)
    client.connect()
    client.idle()
    album_cache = neonmeate.mpd.cache.AlbumCache()
    client.populate_cache(album_cache)
    print(album_cache)
