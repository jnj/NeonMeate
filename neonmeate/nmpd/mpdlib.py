import asyncio
import logging
import os
import re

import mpd as mpd2
from gi.repository import GObject
from ..model import Album, Artist, Song
from functools import partial
import neonmeate.util.thread as thread


class MpdConnectionStatus(GObject.GObject):
    __gsignals__ = {
        'mpd_connected': (GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)
        self._connected = False

    def set_connected(self, connected):
        self._connected = connected
        self.emit('mpd_connected', connected)

    def is_connected(self):
        return self._connected


class Mpd:
    """
    Our client for interacting with the MPD server. The commands are
    asynchronously executed and methods typically accept a callback to
    accept the results of a command. The executor provided to the
    constructor will be used to issue commands to the server.

    """

    def __init__(self, scheduled_executor, configstate, connstatus):
        self._exec = scheduled_executor
        host, port = configstate.get_host_and_port()
        self._configstate = configstate
        self._configstate.connect('notify::host-and-port', self._on_host_chg)
        self._connstatus = connstatus
        self._host = host
        self._port = port
        self._client = mpd2.MPDClient()
        self._client.timeout = 10
        self._client.idletimeout = None
        self._status = {}

    def _on_host_chg(self, state, _):
        self.disconnect()
        self._host, self._port = self._configstate.get_host_and_port()
        self.connect()

    def set_host(self, host):
        self._host = host

    def set_port(self, port):
        self._port = port

    def exec(self, runnable):
        self._exec.execute(runnable)

    def connect(self):
        """
        Connects to the MPD server, blocking until the server
        status is obtained.
        """
        try:
            self._client.connect(self._host, self._port)
            self._connstatus.set_connected(True)
        except ConnectionError:
            logging.error('connection refused')
            self._connstatus.set_connected(False)
            return

        def set_status(s):
            self._status = s

        self.status(set_status)

    def disconnect(self):
        self._client.disconnect()
        self._connstatus.set_connected(False)

    def close(self):
        """Shuts down the client and disconnects from the server."""
        self._client.close()
        self.disconnect()

    def toggle_play_mode(self, name, active):
        """
        Sets a play mode.

        :param name: one of 'repeat', 'random', 'single', or 'consume'.
        :param active: True enables and False disables the mode.
        """
        state = 1 if active else 0
        fn = getattr(self._client, name)
        runnable = partial(fn, state)
        self.exec(runnable)

    def currentsong(self, callback):
        """Fetches the current song."""

        def task():
            record = self._client.currentsong()
            while isinstance(record.get('file', []), list):
                record = self._client.currentsong()
            callback(record)

        self.exec(task)

    def playlistinfo(self, callback):
        """
        This gives the filepath, as well as several of the
        song's tags. A list of dictionaries, one per song,
        will be passed to the callback.
        """
        if not self._connstatus.is_connected():
            callback([])
            return

        def task():
            playqueue = self._client.playlistinfo()
            callback(playqueue)

        self.exec(task)

    def stop_playing(self):
        self.exec(self._client.stop)

    def next_song(self):
        self.exec(self._client.next)

    def prev_song(self):
        self.exec(self._client.previous)

    def toggle_pause(self, should_pause):
        def on_status(mpdstatus):
            if should_pause:
                task = partial(self._client.pause, 1)
            else:
                task = partial(self._client.play, 0)
                if 'pause' == mpdstatus.get('state', 'stop'):
                    task = partial(self._client.pause, 0)
            self.exec(task)

        self.status(on_status)

    def find_artists(self, callback):
        """
        Queries the database for all artists. A list of Artist
        instances will be provided to the callback.
        """
        if not self._connstatus.is_connected():
            callback([])
            return

        def task():
            artists = []
            for a in self._client.list('albumartist'):
                artist = Artist.create(a)
                if artist:
                    artists.append(artist)
            callback(artists)

        self.exec(task)

    def find_albums(self, artist, callback):
        def task():
            songs = self._client.find('albumartist', artist.name)
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
                    s = Song(
                        int(song['track']),
                        int(song.get('disc', 1)),
                        song['title'],
                        song['file']
                    )
                    songlist.append(s)

            albums = []

            for key, songs in songs_by_album.items():
                a = Album(artist, key[0], key[1], songs, dirs_by_album[key][0])
                albums.append(a)
            ordered_albums = Album.sorted_chrono(albums)
            callback(ordered_albums)

        self.exec(task)

    def add_album_to_playlist(self, album):
        """
        Appends an album to the queue.
        :param album: an Album instance containing the songs to add.
        """

        def task():
            for song in album.sorted_songs():
                self._client.add(song.file)

        self.exec(task)

    def remove_album_from_playlist(self, album):
        files = set(s.file for s in album.sorted_songs())

        def removal_task(playlist):
            for t in playlist:
                if t['file'] in files:
                    self._client.deleteid(t['id'])

        def on_playlist(playlist):
            self.exec(removal_task(playlist))

        self.playlistinfo(on_playlist)

    @staticmethod
    def _compute_if_absent(dictionary, key, value):
        v = dictionary.get(key, value)
        dictionary[key] = v
        return v

    def status(self, callback):
        if not self._connstatus.is_connected():
            callback({})
            return

        def task():
            callback(self._client.status())

        self.exec(task)

    def clear_playlist(self):
        def task():
            self._client.clear()

        self.exec(task)

    def delete_playlist_item(self, index):
        def task():
            self._client.delete(index)

        self.exec(task)


# noinspection PyUnresolvedReferences
class MpdState(GObject.GObject):
    """
    Used by the heartbeat to track the player state.
    """

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
    songseconds = GObject.Property(type=float, default=1)
    elapsedseconds = GObject.Property(type=float, default=0)
    updatingdb = GObject.Property(type=str, default='0')
    synth_props = {'songseconds', 'elapsedseconds', 'updatingdb'}

    def __init__(self):
        GObject.GObject.__init__(self)
        self._time_pattern = re.compile(r'^\d+(\.\d+)?$')

    def __str__(self):
        s = ''
        for p in self.list_properties():
            if p.name not in self.synth_props:
                s += f'{p.name}={self.get_property(p.name)}\n'
        return s

    def reset(self):
        self.set_property('duration', '1')
        for name in ['repeat', 'random', 'elapsed', 'consume',
                     'single', 'playlistlength', 'updatingdb']:
            self.set_property(name, '0')
        for name in ['songid', 'playlist']:
            self.set_property(name, '-1')
        self.set_property('state', '')
        self.set_property('songseconds', 1)
        self.set_property('elapsedseconds', 0)

    def update(self, status):
        for p in self.list_properties():
            if p.name not in self.synth_props:
                new_val = status.get(p.name, p.default_value)
                self._update_if_changed(p.name, new_val)
        self._update_elapsed_time()
        self._check_updating_db(status)

    def _update_if_changed(self, name, newval):
        current = self.get_property(name)
        if current != newval:
            self.set_property(name, newval)

    def _check_updating_db(self, status):
        updating = status.get('updating_db', '0')
        self._update_if_changed('updatingdb', updating)

    def _update_elapsed_time(self):
        elapsed_secs = float(self.get_property('elapsed'))
        duration_str = self.get_property('duration')
        if self._time_pattern.search(duration_str):
            total_secs = float(duration_str)
            self._update_if_changed('songseconds', total_secs)
            self._update_if_changed('elapsedseconds', elapsed_secs)


# noinspection PyUnresolvedReferences
class MpdHeartbeat(GObject.GObject):
    """
    Ideally MPD would allow a client to register itself to receive
    status pushes, so that a client can update in a reactive way as
    needed. MPD currently does not support that kind of model; the
    idle command is sort of in that vein, but isn't all that useful.
    So instead we create a heartbeat with the server that polls on an
    interval.

    The only needed interaction with an instance of the heartbeat is
    to call connect() to receive event notification. It also will need
    to be started and stopped.

    """

    # These signals will be emitted when player events are detected.
    __gsignals__ = {
        'playlist_changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'song_elapsed': (GObject.SignalFlags.RUN_FIRST, None, (float, float)),
        'song_playing_status': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'song_changed': (
            GObject.SignalFlags.RUN_FIRST, None, (str, str, str, str)),
        'no_song': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'playback_mode_toggled': (
            GObject.SignalFlags.RUN_FIRST, None, (str, bool)),
        'updatingdb': (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, client, millis_interval, executor):
        """
        The executor will be used to periodically query the server.
        """
        GObject.GObject.__init__(self)
        self.logger = logging.getLogger(__name__)
        self._client = client
        self._thread = executor
        self._delay = millis_interval / 1000.0
        self._mpd_status = {}
        self._state = MpdState()
        for prop, fn in {
            'songid': self._on_song_change,
            'playlist': self._on_playlist_change,
            'playlistlength': self._on_playlistlength_change,
            'updatingdb': self._on_updating,
            'consume': self._on_mode_change,
            'random': self._on_mode_change,
            'repeat': self._on_mode_change,
            'single': self._on_mode_change,
            'elapsedseconds': self._on_elapsed_change,
            'songseconds': self._on_total_seconds_change,
            'state': self._on_state_change
        }.items():
            self._state.connect(f'notify::{prop}', fn)
        self._scheduled_hb = None

    def start(self):
        if self._scheduled_hb is None:
            self._scheduled_hb = self._thread.schedule_periodic(
                self._delay,
                self._on_hb_interval
            )

    def stop(self):
        self._state.reset()
        if self._scheduled_hb:
            self._scheduled_hb.cancel()
            self._scheduled_hb = None

    def connect(self, signal_name, handler, *args):
        """
        Clients should use this method to subscribe to the events this
        class emits. The handler will be called on the main GTK thread.

        """
        thread.signal_subcribe_on_main(super(MpdHeartbeat, self).connect,
                                       signal_name, handler, *args)

    def _on_hb_interval(self):
        def on_status(status):
            self._mpd_status = status
            self._state.update(self._mpd_status)

        # Not strictly needed since the hb is typically created
        # with the same thread that is passed to the mpd client.
        def on_hb_thread(status):
            self._thread.execute(partial(on_status, status))

        self._client.status(on_hb_thread)
        return True

    def _on_state_change(self, obj, spec):
        self.emit('song_playing_status', self._state.get_property(spec.name))

    def _on_song_change(self, obj, spec):
        songid = self._state.get_property(spec.name)

        if songid == '-1':
            self.emit('no_song')
            return

        def on_current_song(song_info):
            self.logger.info(f'current song: {str(song_info)}')
            try:
                self.emit('song_changed',
                          song_info['artist'],
                          song_info['title'],
                          song_info['album'],
                          song_info['file'])
            except KeyError as e:
                self.logger.exception(e)

        self._client.currentsong(on_current_song)

    def _on_playlist_change(self, obj, spec):
        self.emit('playlist-changed')

    def _on_playlistlength_change(self, obj, spec):
        self.emit('playlist-changed')

    def _on_updating(self, obj, spec):
        propval = self._state.get_property(spec.name)
        self.emit('updatingdb', propval != '0')

    def _on_mode_change(self, obj, spec):
        propval = self._state.get_property(spec.name)
        self.emit('playback-mode-toggled', spec.name, propval != '0')

    def _on_elapsed_change(self, obj, spec):
        self._on_total_seconds_change(obj, spec)

    def _on_total_seconds_change(self, obj, spec):
        elapsed = self._state.get_property('elapsedseconds')
        total = self._state.get_property('songseconds')
        self.emit('song_elapsed', elapsed, total)

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
    # album_cache = neonmeate.nmpd.cache.AlbumCache()
    # client.populate_cache(album_cache)
    # print(album_cache)
