import neonmeate.ui.toolkit as tk

from gi.repository import Gdk, GdkPixbuf, Gtk

from .toolkit import Scrollable
from .artists import Artists
from .controls import ControlButtons
from .songprogress import SongProgress
from ..mpd import mpdlib as nmpd


class App(Gtk.ApplicationWindow):
    def __init__(self, mpdclient, covers, cache):
        Gtk.Window.__init__(self, title="NeonMeate")
        self.heartbeat = nmpd.MpdHeartbeat(mpdclient, 200)
        self.heartbeat.start()
        self.mpdclient = mpdclient
        self.album_cache = cache

        self.set_default_size(4 * 200 + 3 * 5, 4 * 200 + 3 * 5)

        self.titlebar = Gtk.HeaderBar()
        self.titlebar.set_title("NeonMeate")
        self.titlebar.set_show_close_button(True)
        self.set_titlebar(self.titlebar)

        self.controlbuttons = ControlButtons()
        self.songprogress = SongProgress()
        self.songprogress.set_fraction(0)

        self.actionbar = Gtk.ActionBar()
        self.actionbar.pack_start(self.controlbuttons)
        self.actionbar.pack_start(self.songprogress)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.main_box)

        self.stack = Gtk.Stack()
        self.main_box.pack_start(self.stack, True, True, 0)
        self.main_box.pack_end(self.actionbar, False, False, 0)

        # self.add(self.panes)
        # artist_album_table = table.Table(['Artist', 'Album'], [str, str])
        # self.artist_list = artist_album_table
        self.artists = Artists(self.album_cache)
        self.playlist = tk.Table(['Artist', 'Title'], [str, str])
        current_queue = self.mpdclient.playlistinfo()
        for i in current_queue:
            self.playlist.add([i['artist'], i['title']])

        self.playlist_window = Scrollable()
        self.playlist_window.add_content(self.playlist.as_widget())

        self.stack.add_titled(self.artists, 'artists', 'Artists')
        self.stack.add_titled(self.playlist_window, 'playlist', 'Playlist')
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.titlebar.pack_start(self.stack_switcher)

        # self.artists_window.add(self.artist_list.as_widget())
        # self.panes.pack1(self.artists_window)

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

        self.controlbuttons.connect('neonmeate_stop_playing', self.on_stop)
        self.controlbuttons.connect('neonmeate_start_playing', self.on_start)
        self.controlbuttons.connect('neonmeate_toggle_pause', self.on_pause)
        self.heartbeat.connect('song_played_percent', self._on_song_percent)
        self.heartbeat.connect('song_playing_status', self._on_song_playing_status)
        self.heartbeat.connect('song_changed', self._on_song_changed)
        self.heartbeat.connect('no_song', lambda hb: self._on_song_changed(hb, None, None))

    def _on_song_changed(self, hb, artist, title):
        title_text = 'NeonMeate'
        if artist and title:
            title_text = f'{artist} - {title}'
        self.titlebar.set_title(title_text)

    def _on_song_playing_status(self, hb, status):
        if status == 'play':
            self.controlbuttons.set_paused(False, False)
        elif status == 'pause':
            self.controlbuttons.set_paused(True, False)
        elif status == 'stop':
            self.controlbuttons.set_paused(False, True)

    def _on_song_percent(self, hb, fraction):
        self.songprogress.set_fraction(fraction)

    def on_start(self, x):
        self.mpdclient.toggle_pause(0)

    def on_pause(self, x):
        self.mpdclient.toggle_pause(1)

    def on_stop(self, x):
        self.mpdclient.stop_playing()
        self.songprogress.set_fraction(0)
