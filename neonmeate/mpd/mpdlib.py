import mpd as mpd2
from gi.repository import GLib, GObject

import neonmeate.nmasync as nmasync


class Mpd:
    def __init__(self, host='localhost', port=6600):
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
            # print(changed)

    def playlist(self):
        """
        Returns the songs in the current playlist.
        :return: a list of filenames.
        """
        return self._client.playlist()

    def playlistinfo(self):
        """
        Returns the songs in the current playlist. This
        gives the filepath, several of the song's tags.
        :return: a list of dictionaries, one per song
        """
        return self._client.playlistinfo()

    def stop_playing(self):
        nmasync.RunAsync(self._client.stop)

    def next_song(self):
        nmasync.RunAsync(self._client.next)

    def prev_song(self):
        nmasync.RunAsync(self._client.previous)

    def toggle_pause(self, should_pause):
        mpdstatus = self.status()
        if should_pause:
            task = self._pause
        else:
            task = self._play_first_song
            if 'pause' == mpdstatus.get('state', 'stop'):
                task = self._unpause
        nmasync.RunAsync(task)

    def _pause(self):
        self._client.pause(1)

    def _play_first_song(self):
        self._client.play(0)

    def _unpause(self):
        self._client.pause(0)

    def find_artists(self):
        return self._client.list('artist')

    def find_albums(self, artist):
        songs = self._client.find('artist', artist)
        songs_by_album = {}

        for song in songs:
            if 'album' in song:
                album = song['album']
                songlist = songs_by_album.get(album, [])
                songlist.append(song)
                songs_by_album[album] = songlist

        return songs_by_album

    def status(self):
        return self._client.status()

    def clear_playlist(self):
        self._client.send_playlistclear()

    def populate_cache(self, albumcache):
        artists = self._client.list('artist')
        for artist in artists:
            albums = self.find_albums(artist)
            for album, songlist in albums.items():
                albumcache.add(artist, album, songlist)


class MpdState(GObject.GObject):
    duration = GObject.Property(type=str, default='1')
    repeat = GObject.Property(type=str, default='0')
    random = GObject.Property(type=str, default='0')
    elapsed = GObject.Property(type=str, default='0')
    songid = GObject.Property(type=str, default='-1')
    consume = GObject.Property(type=str, default='0')
    single = GObject.Property(type=str, default='0')
    state = GObject.Property(type=str, default='stop')
    playlist = GObject.Property(type=str, default='-1')
    playlistlength = GObject.Property(type=str, default='0')
    elapsedtime = GObject.Property(type=float, default=0.0)
    synth_props = {'elapsedtime'}

    def __init__(self):
        GObject.GObject.__init__(self)

    def update(self, status):
        for p in self.list_properties():
            if p.name not in self.synth_props:
                new_val = status.get(p.name, p.default_value)
                self._update_if_changed(p.name, new_val)
        self._update_elapsed_time()

    def _update_if_changed(self, name, newval):
        current = self.get_property(name)
        if current != newval:
            # print(f"updating property {name} from {current} to {newval}")
            self.set_property(name, newval)

    def _update_elapsed_time(self):
        e = float(self.get_property('elapsed'))
        t = float(self.get_property('duration'))
        self._update_if_changed('elapsedtime', round(e / t, 3))


class MpdHeartbeat(GObject.GObject):
    __gsignals__ = {
        'playlist_changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song_played_percent': (GObject.SignalFlags.RUN_FIRST, None, (float,)),
        'song_playing_status': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'song_changed': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
        'no_song': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, client, millis_interval):
        GObject.GObject.__init__(self)
        self._client = client
        self._thread = nmasync.PeriodicTask(millis_interval, self._on_hb_interval)
        self._mpd_status = {}
        self._state = MpdState()

        for prop, fn in {
            'songid': self._on_song_change,
            'playlist': self._on_playlist_change,
            'playlistlength': self._on_playlistlength_change,
            'consume': self._on_consume_change,
            'random': self._on_random_change,
            'repeat': self._on_repeat_change,
            'single': self._on_single_change,
            'elapsedtime': self._on_elapsed_change,
            'state': self._on_state_change
        }.items():
            self._state.connect(f'notify::{prop}', fn)

    def start(self):
        self._thread.start()

    def stop(self):
        self._thread.stop()

    def connect(self, signal_name, handler, *args):
        def wrapped_handler(obj, *a):
            GLib.idle_add(handler, obj, *a)
        super(MpdHeartbeat, self).connect(signal_name, wrapped_handler, *args)

    def _on_hb_interval(self):
        self._mpd_status = self._client.status()
        self._state.update(self._mpd_status)
        return True

    def _on_single_change(self, obj, spec):
        pass

    def _on_state_change(self, obj, spec):
        self.emit('song_playing_status', self._state.get_property(spec.name))

    def _on_song_change(self, obj, spec):
        songid = self._state.get_property(spec.name)
        if songid == '-1':
            self.emit('no_song')
            return
        song_info = self._client.currentsong()
        self.emit('song_changed', song_info['artist'], song_info['title'])

    def _on_playlist_change(self, obj, spec):
        self.emit('playlist-changed')

    def _on_playlistlength_change(self, obj, spec):
        self.emit('playlist-changed')

    def _on_consume_change(self, obj, spec):
        pass

    def _on_repeat_change(self, obj, spec):
        pass

    def _on_random_change(self, obj, spec):
        pass

    def _on_elapsed_change(self, obj, spec):
        self.emit('song_played_percent', self._state.get_property(spec.name))

    def _mpd_state(self):
        return self._mpd_status.get('state', 'unknown')

    def _state_is(self, state_value):
        return self._mpd_state() == state_value

    def _is_playing(self):
        return self._state_is('play')

    def _is_paused(self):
        return self._state_is('pause')


if __name__ == '__main__':
    client = Mpd('localhost', 6600)
    client.connect()
    print(client.status())
    # client.idle()
    # album_cache = neonmeate.mpd.cache.AlbumCache()
    # client.populate_cache(album_cache)
    # print(album_cache)
