from gi.repository import Gtk

from .artistsalbums import ArtistsAlbums
from .controls import ControlButtons, PlayModeButtons
from .nowplaying import NowPlaying
from .playlist import Playlist
from .songprogress import SongProgress
from ..mpd import mpdlib as nmpd


class App(Gtk.ApplicationWindow):
    PlayStatus = {
        'play': (False, False),
        'pause': (True, False),
        'stop': (False, True)
    }

    # noinspection PyUnresolvedReferences
    def __init__(self, mpdclient, executor, cache, art_cache):
        Gtk.ApplicationWindow.__init__(self, title="NeonMeate")
        self._executor = executor
        self._heartbeat = nmpd.MpdHeartbeat(mpdclient, 200)
        self._heartbeat.start()
        self._mpdclient = mpdclient
        self._album_cache = cache
        self._art_cache = art_cache
        self.set_default_size(600, 600)
        self._titlebar = Gtk.HeaderBar()
        self._titlebar.set_title("NeonMeate")
        self._titlebar.set_show_close_button(True)
        self.set_titlebar(self._titlebar)
        self._controlbuttons = ControlButtons()
        self._playmodebuttons = PlayModeButtons()
        self._songprogress = SongProgress()
        self._songprogress.set_fraction(0)
        self._actionbar = Gtk.ActionBar()
        self._actionbar.pack_start(self._controlbuttons)
        self._actionbar.pack_start(self._songprogress)
        self._actionbar.pack_start(self._playmodebuttons)
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._main_box)
        self._stack = Gtk.Stack()
        self._main_box.pack_start(self._stack, True, True, 0)
        self._main_box.pack_end(self._actionbar, False, False, 0)

        self._artists = ArtistsAlbums(self._album_cache, self._art_cache)
        self._playlist = Playlist()
        self._playlist.connect('key-press-event', self._on_playlist_key)
        self._update_playlist(None)

        self._now_playing = NowPlaying(self._album_cache, self._art_cache, self._executor)
        self._stack.add_titled(self._artists, 'artists', 'Artists')
        self._stack.add_titled(self._playlist, 'playlist', 'Playlist')
        self._stack.add_titled(self._now_playing, 'now_playing', 'Playing')
        self._stack_switcher = Gtk.StackSwitcher()
        self._stack_switcher.set_stack(self._stack)
        self._titlebar.pack_start(self._stack_switcher)

        self._controlbuttons.connect('neonmeate_stop_playing', self.on_stop)
        self._controlbuttons.connect('neonmeate_start_playing', self.on_start)
        self._controlbuttons.connect('neonmeate_toggle_pause', self.on_pause)
        self._controlbuttons.connect('neonmeate_prev_song', self.on_prev_song)
        self._controlbuttons.connect('neonmeate_next_song', self.on_next_song)
        self._playmodebuttons.subscribe_to_signal('neonmeate_playmode_toggle', self._on_user_mode_toggle)
        self._heartbeat.connect('song_played_percent', self._on_song_percent)
        self._heartbeat.connect('song_playing_status', self._on_song_playing_status)
        self._heartbeat.connect('song_changed', self._on_song_changed)
        self._heartbeat.connect('no_song', lambda hb: self._on_song_changed(hb, None, None, None))
        self._heartbeat.connect('playlist-changed', self._update_playlist)
        self._heartbeat.connect('playback-mode-toggled', self._on_mode_change())

    def _on_user_mode_toggle(self, _, name, is_active):
        self._mpdclient.toggle_play_mode(name, is_active)

    def _on_mode_change(self):
        def handler(_, name, is_active):
            self._playmodebuttons.on_mode_change(name, is_active)

        return handler

    def _on_playlist_key(self, obj, key):
        print(f"playlist key pressed {key}")

    def _update_playlist(self, obj):
        self._playlist.clear()
        current_queue = self._mpdclient.playlistinfo()
        for i in current_queue:
            try:
                if 'artist' not in i:
                    continue
                artist = i['artist']
                album = i['album']
                title = i['title']
                if isinstance(title, list):
                    title = ' - '.join(title)
                self._playlist.add_playlist_item([artist, album, int(i['track']), title])
                cover_path = self._album_cache.cover_art_path(artist, album)
                if cover_path is None:
                    print(f"Cover not found for {artist} {album}")
                else:
                    self._art_cache.fetch(cover_path, None, None)
            except KeyError as e:
                print(f"Failed to find key in {i}")
                raise e

    def _on_song_changed(self, hb, artist, title, album):
        title_text = 'NeonMeate'
        if artist and title:
            title_text = f'{artist} - {title}'
        self._titlebar.set_title(title_text)
        if artist is None:
            self._now_playing.clear()
            return
        covpath = self._album_cache.cover_art_path(artist, album)
        self._art_cache.fetch(covpath, None, None)
        self._now_playing.on_playing(artist, album, covpath)

    def _on_song_playing_status(self, hb, status):
        paused, stopped = App.PlayStatus.get(status, (False, False))
        self._controlbuttons.set_paused(paused, stopped)

    def _on_song_percent(self, hb, fraction):
        self._songprogress.set_fraction(fraction)
        self._songprogress.queue_draw()

    def on_start(self, x):
        self._mpdclient.toggle_pause(0)

    def on_pause(self, x):
        self._mpdclient.toggle_pause(1)

    def on_stop(self, x):
        self._mpdclient.stop_playing()
        self._songprogress.set_fraction(0)

    def on_prev_song(self, x):
        self._mpdclient.prev_song()

    def on_next_song(self, x):
        self._mpdclient.next_song()
