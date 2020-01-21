from gi.repository import GdkPixbuf, Gtk

from .artistsalbums import ArtistsAlbums
from .nowplaying import NowPlaying
from .controls import ControlButtons
from .playlist import Playlist
from .songprogress import SongProgress
from ..mpd import mpdlib as nmpd


class App(Gtk.ApplicationWindow):
    PlayStatus = {
        'play': (False, False),
        'pause': (True, False),
        'stop': (False, True)
    }

    def __init__(self, mpdclient, cache, art_cache):
        Gtk.Window.__init__(self, title="NeonMeate")
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
        self._songprogress = SongProgress()
        self._songprogress.set_fraction(0)
        self._actionbar = Gtk.ActionBar()
        self._actionbar.pack_start(self._controlbuttons)
        self._actionbar.pack_start(self._songprogress)
        self._main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self._main_box)
        self._stack = Gtk.Stack()
        self._main_box.pack_start(self._stack, True, True, 0)
        self._main_box.pack_end(self._actionbar, False, False, 0)

        self._artists = ArtistsAlbums(self._album_cache, self._art_cache)
        self._playlist = Playlist()
        self._playlist.connect('key-press-event', self._on_playlist_key)
        self._update_playlist(None)

        self._now_playing = NowPlaying(self._album_cache, self._art_cache)
        self._stack.add_titled(self._artists, 'artists', 'Artists')
        self._stack.add_titled(self._playlist, 'playlist', 'Playlist')
        self._stack.add_titled(self._now_playing, 'now_playing', 'Playing')
        self._stack_switcher = Gtk.StackSwitcher()
        self._stack_switcher.set_stack(self._stack)
        self._titlebar.pack_start(self._stack_switcher)

        self._controlbuttons.connect('neonmeate_stop_playing', self.on_stop)
        self._controlbuttons.connect('neonmeate_start_playing', self.on_start)
        self._controlbuttons.connect('neonmeate_toggle_pause', self.on_pause)

        self._heartbeat.connect('song_played_percent', self._on_song_percent)
        self._heartbeat.connect('song_playing_status', self._on_song_playing_status)
        self._heartbeat.connect('song_changed', self._on_song_changed)
        self._heartbeat.connect('no_song', lambda hb: self._on_song_changed(hb, None, None))
        self._heartbeat.connect('playlist-changed', self._update_playlist)

    def _on_playlist_key(self, obj, key):
        print(f"playlist key pressed {key}")

    def _update_playlist(self, obj):
        self._playlist.clear()
        current_queue = self._mpdclient.playlistinfo()
        for i in current_queue:
            try:
                self._playlist.add_playlist_item([i['artist'], i['album'], int(i['track']), i['title']])
            except KeyError as e:
                print(f"Failed to find key in {i}")
                raise e

    def _on_song_changed(self, hb, artist, title):
        title_text = 'NeonMeate'
        if artist and title:
            title_text = f'{artist} - {title}'
        self._titlebar.set_title(title_text)

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
