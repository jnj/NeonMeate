import neonmeate.ui.toolkit as tk

from gi.repository import Gdk, GdkPixbuf, Gtk

from .toolkit import Scrollable
from .artists import Artists
from .controls import ControlButtons
from .songprogress import SongProgress
from ..mpd import mpdlib as nmpd


class App(Gtk.ApplicationWindow):
    def __init__(self, mpdclient, covers, cache, art_cache):
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

        self._artists = Artists(self._album_cache, self._art_cache)
        self._playlist = tk.Table(['Artist', 'Title'], [str, str])
        current_queue = self._mpdclient.playlistinfo()
        for i in current_queue:
            self._playlist.add([i['artist'], i['title']])

        self.playlist_window = Scrollable()
        self.playlist_window.add_content(self._playlist.as_widget())

        self._stack.add_titled(self._artists, 'artists', 'Artists')
        self._stack.add_titled(self.playlist_window, 'playlist', 'Playlist')
        self._stack_switcher = Gtk.StackSwitcher()
        self._stack_switcher.set_stack(self._stack)
        self._titlebar.pack_start(self._stack_switcher)

        self.covers = covers
        self.grid = Gtk.Grid()
        self.grid.set_row_homogeneous(True)
        self.grid.set_column_homogeneous(True)
        self.grid.set_column_spacing(5)
        self.grid.set_row_spacing(5)

        attach_row = 0
        attach_col = 0
        count = 0
        width = 10

        for cover in self.covers:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(cover)
            pixbuf = pixbuf.scale_simple(200, 200, GdkPixbuf.InterpType.BILINEAR)
            img = Gtk.Image.new_from_pixbuf(pixbuf)

            if count == width:
                attach_row += 1
                attach_col = 0
                count = 0

            self.grid.attach(img, attach_col, attach_row, 1, 1)
            attach_col += 1
            count += 1

        self._controlbuttons.connect('neonmeate_stop_playing', self.on_stop)
        self._controlbuttons.connect('neonmeate_start_playing', self.on_start)
        self._controlbuttons.connect('neonmeate_toggle_pause', self.on_pause)
        self._heartbeat.connect('song_played_percent', self._on_song_percent)
        self._heartbeat.connect('song_playing_status', self._on_song_playing_status)
        self._heartbeat.connect('song_changed', self._on_song_changed)
        self._heartbeat.connect('no_song', lambda hb: self._on_song_changed(hb, None, None))

    def _on_song_changed(self, hb, artist, title):
        title_text = 'NeonMeate'
        if artist and title:
            title_text = f'{artist} - {title}'
        self._titlebar.set_title(title_text)

    def _on_song_playing_status(self, hb, status):
        if status == 'play':
            self._controlbuttons.set_paused(False, False)
        elif status == 'pause':
            self._controlbuttons.set_paused(True, False)
        elif status == 'stop':
            self._controlbuttons.set_paused(False, True)

    def _on_song_percent(self, hb, fraction):
        self._songprogress.set_fraction(fraction)

    def on_start(self, x):
        self._mpdclient.toggle_pause(0)

    def on_pause(self, x):
        self._mpdclient.toggle_pause(1)

    def on_stop(self, x):
        self._mpdclient.stop_playing()
        self._songprogress.set_fraction(0)
