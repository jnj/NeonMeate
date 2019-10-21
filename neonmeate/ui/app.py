import neonmeate.ui.toolkit as tk

from gi.repository import Gdk, GdkPixbuf, Gtk

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
        self.titlebar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.controlbuttons = ControlButtons()
        self.titlebar_box.pack_start(self.controlbuttons, False, False, 0)
        self.songprogress = SongProgress()
        self.songprogress.show()
        self.songprogress.set_fraction(0)
        # self.titlebar_box.pack_start(self.songprogress, False, False, 0)
        self.titlebar.pack_start(self.titlebar_box)
        self.titlebar.add(self.songprogress)

        self.panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(self.panes)

        # artist_album_table = table.Table(['Artist', 'Album'], [str, str])
        # self.artist_list = artist_album_table
        self.artists = Artists()
        for artist in self.album_cache.all_artists():
            self.artists.add_row(artist)

        # for artist, album in self.album_cache.all_artists_and_albums():
        #     if artist != '' and album != '':
        #         artist_album_table.add([artist, album])

        self.artists_vp = Gtk.Viewport()
        self.artists_window = Gtk.ScrolledWindow()
        self.artists_vp.add(self.artists)
        self.artists_window.add(self.artists_vp)

        # self.artists_window.add(self.artist_list.as_widget())
        self.panes.pack1(self.artists_window)

        self.covers = covers
        self.grid = Gtk.Grid()
        self.grid.set_row_homogeneous(True)
        self.grid.set_column_homogeneous(True)
        self.grid.set_column_spacing(5)
        self.grid.set_row_spacing(5)

        self.scrolled = Gtk.ScrolledWindow()
        self.covers_and_playlist = Gtk.VPaned()

        covers_scrollable = Gtk.ScrolledWindow()
        covers_scrollable.add(self.grid)
        self.covers_and_playlist.pack2(covers_scrollable)

        playlist_scrollable = Gtk.ScrolledWindow()
        self.covers_and_playlist.pack1(playlist_scrollable)
        self.scrolled.add(self.covers_and_playlist)
        self.panes.pack2(self.scrolled)
        self.panes.set_position(200)

        self.queue_table = tk.Table(['Artist', 'Title'], [str, str])
        current_queue = self.mpdclient.playlistinfo()
        for i in current_queue:
            self.queue_table.add([i['artist'], i['title']])
        playlist_scrollable.add(self.queue_table.as_widget())

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

    def _on_song_playing_status(self, hb, status):
        if status == 'play':
            self.controlbuttons.set_paused(False, False)
        elif status == 'pause':
            self.controlbuttons.set_paused(True, False)
        elif status == 'stop':
            self.controlbuttons.set_paused(False, True)

    def _on_song_percent(self, hb, pct):
        self.songprogress.set_fraction(pct / 100.0)

    def on_start(self, x):
        self.mpdclient.toggle_pause(0)

    def on_pause(self, x):
        self.mpdclient.toggle_pause(1)

    def on_stop(self, x):
        self.mpdclient.stop_playing()
        self.songprogress.set_fraction(0)
