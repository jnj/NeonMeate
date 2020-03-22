import asyncio
import logging
import os
import re

import mpd as mpd2
from gi.repository import GObject
from ..model import Album, Artist, Song
from functools import partial
import neonmeate.nmasync as nmasync


class Mpd:
    def __init__(self, scheduled_executor, host='localhost', port=6600):
        self._exec = scheduled_executor
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

    def toggle_play_mode(self, name, active):
        state = 1 if active else 0
        fn = getattr(self._client, name)
        runnable = partial(fn, state)
        self._exec.execute(runnable)

    def currentsong(self, callback):
        def task():
            record = self._client.currentsong()
            while isinstance(record.get('file', []), list):
                record = self._client.currentsong()
            callback(record)

        self._exec.execute(task)

    def playlistinfo(self, callback):
        """
        This gives the filepath, as well as several of the
        song's tags. A list of dictionaries, one per song,
        will be passed to the callback.
        """

        def task():
            playqueue = self._client.playlistinfo()
            callback(playqueue)

        self._exec.execute(task)

    def stop_playing(self):
        self._exec.execute(self._client.stop)

    def next_song(self):
        self._exec.execute(self._client.next)

    def prev_song(self):
        self._exec.execute(self._client.previous)

    def toggle_pause(self, should_pause):
        mpdstatus = self.status()
        if should_pause:
            task = partial(self._client.pause, 1)
        else:
            task = partial(self._client.play, 0)
            if 'pause' == mpdstatus.get('state', 'stop'):
                task = partial(self._client.pause, 0)
        self._exec.execute(task)

    def find_artists(self):
        # todo exec on executor
        return [Artist(a) for a in self._client.list('artist') if len(a) > 0]

    def find_albums(self, artist):
        # todo exec on executor
        songs = self._client.find('artist', artist)
        songs_by_album = {}
        dirs_by_album = {}

        for song in songs:
            if 'album' in song:
                album_name = song['album']
                date = int(song['date'])
                directory = os.path.dirname(song['file'])
                key = (album_name, date)
                songlist = Mpd._compute_if_absent(songs_by_album, key, [])
                dirs = Mpd._compute_if_absent(dirs_by_album, key, [])
                dirs.append(directory)
                s = Song(int(song['track']), int(song.get('disc', 1)), song['title'])
                songlist.append(s)

        albums = []
        for key, songs in songs_by_album.items():
            a = Album(Artist(artist), key[0], key[1], songs, dirs_by_album[key][0])
            albums.append(a)

        return Album.sorted_chrono(albums)

    @staticmethod
    def _compute_if_absent(dictionary, key, value):
        v = dictionary.get(key, value)
        dictionary[key] = v
        return v

    def status(self):
        # todo exec on executor
        return self._client.status()

    def clear_playlist(self):
        self._client.send_playlistclear()


# noinspection PyUnresolvedReferences
class MpdState(GObject.GObject):
    duration = GObject.Property(type=str, default='1')
    repeat = GObject.Property(type=str, default='0')
    random = GObject.Property(type=str, default='0')
    elapsed = GObject.Property(type=str, default='0')
    songid = GObject.Property(type=str, default='-1')
    consume = GObject.Property(type=str, default='0')
    single = GObject.Property(type=str, default='0')
    state = GObject.Property(type=str, default='')
    playlist = GObject.Property(type=str, default='-1')
    playlistlength = GObject.Property(type=str, default='0')
    elapsedtime = GObject.Property(type=float, default=0.0)
    synth_props = {'elapsedtime'}

    def __init__(self):
        GObject.GObject.__init__(self)
        self._time_pattern = re.compile(r'^\d+(\.\d+)?$')

    def __str__(self):
        s = ''
        for p in self.list_properties():
            if p.name not in self.synth_props:
                s += f'{p.name}={self.get_property(p.name)}\n'
        return s

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
        duration = self.get_property('duration')
        if self._time_pattern.search(duration):
            t = float(duration)
            self._update_if_changed('elapsedtime', round(e / t, 3))


# noinspection PyUnresolvedReferences
class MpdHeartbeat(GObject.GObject):
    __gsignals__ = {
        'playlist_changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song_played_percent': (GObject.SignalFlags.RUN_FIRST, None, (float,)),
        'song_playing_status': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'song_changed': (GObject.SignalFlags.RUN_FIRST, None, (str, str, str, str)),
        'no_song': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'playback_mode_toggled': (GObject.SignalFlags.RUN_FIRST, None, (str, bool))
    }

    def __init__(self, client, millis_interval, executor):
        GObject.GObject.__init__(self)
        self._client = client
        self._thread = executor
        self._delay = millis_interval / 1000.0
        self._mpd_status = {}
        self._state = MpdState()

        for prop, fn in {
            'songid': self._on_song_change,
            'playlist': self._on_playlist_change,
            'playlistlength': self._on_playlistlength_change,
            'consume': self._on_mode_change,
            'random': self._on_mode_change,
            'repeat': self._on_mode_change,
            'single': self._on_mode_change,
            'elapsedtime': self._on_elapsed_change,
            'state': self._on_state_change
        }.items():
            self._state.connect(f'notify::{prop}', fn)

    def start(self):
        self._thread.start()
        self._thread.schedule_periodic(self._delay, self._on_hb_interval)

    def stop(self):
        self._thread.stop()

    def connect(self, signal_name, handler, *args):
        nmasync.signal_subcribe_on_main(super(MpdHeartbeat, self).connect, signal_name, handler, *args)

    def _on_hb_interval(self):
        self._mpd_status = self._client.status()
        self._state.update(self._mpd_status)
        return True

    def _on_state_change(self, obj, spec):
        self.emit('song_playing_status', self._state.get_property(spec.name))

    def _on_song_change(self, obj, spec):
        songid = self._state.get_property(spec.name)

        if songid == '-1':
            self.emit('no_song')
            return

        def on_current_song(song_info):
            logging.info(f'current song: {str(song_info)}')
            try:
                self.emit('song_changed',
                          song_info['artist'],
                          song_info['title'],
                          song_info['album'],
                          song_info['file'])
            except KeyError as e:
                logging.exception(e)

        self._client.currentsong(on_current_song)

    def _on_playlist_change(self, obj, spec):
        self.emit('playlist-changed')

    def _on_playlistlength_change(self, obj, spec):
        self.emit('playlist-changed')

    def _on_mode_change(self, obj, spec):
        propval = self._state.get_property(spec.name)
        self.emit('playback-mode-toggled', spec.name, propval != '0')

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
    event_loop = asyncio.new_event_loop()

    # client = Mpd('localhost', 6600)
    # client.connect()
    # hb = MpdHeartbeat(client, 900)
    # hb.start()
    # while True:
    #     pass
    # print(client.status())
    # client.idle()
    # album_cache = neonmeate.mpd.cache.AlbumCache()
    # client.populate_cache(album_cache)
    # print(album_cache)
