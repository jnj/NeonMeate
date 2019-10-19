import os
import sys
import math
import threading
import time
import gi
from gi._gi import GObject

gi.require_version('Gtk', '3.0')
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

import neonmeate.mpdlib as nmpd
import neonmeate.cache as nmcache
import neonmeate.ui.table as table
import neonmeate.ui.controls as controls


class MyWindow(Gtk.ApplicationWindow):
    def __init__(self, mpdclient, covers, cache):
        Gtk.Window.__init__(self, title="PyMusic")
        self.mpdclient = mpdclient
        self.album_cache = cache
        self.set_default_size(4 * 200 + 3 * 5, 4 * 200 + 3 * 5)
        self.titlebar = Gtk.HeaderBar()
        self.titlebar.set_title("NeonMeate")
        self.titlebar.set_show_close_button(True)
        self.set_titlebar(self.titlebar)
        self.titlebar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.titlebar_box.pack_start(controls.PlayPauseButton(), False, False, 0)
        self.titlebar.pack_start(self.titlebar_box)

        self.panes = Gtk.HPaned()
        self.add(self.panes)

        artist_album_table = table.Table(['Artist', 'Album'], [str, str])
        self.artist_list = artist_album_table
        for artist, album in self.album_cache.all_artists_and_albums():
            if artist != '' and album != '':
                artist_album_table.add([artist, album])

        self.artists_window = Gtk.ScrolledWindow()
        self.artists_window.add(self.artist_list.as_widget())
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

        self.queue_table = table.Table(['Artist', 'Title'], [str, str])
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


def each_cover(path):
    if os.path.isfile(path) and path[-9:] == 'cover.jpg':
        yield path
    elif os.path.isdir(path):
        children = os.listdir(path)
        for c in children:
            for f in each_cover(os.path.join(path, c)):
                yield f


class Handler:
    def on_destroy(self, *args):
        Gtk.main_quit()

    def onButtonPressed(self, button):
        pass


def main(args):
    # builder = Gtk.Builder()
    # builder.add_from_file("/home/josh/neonmeate.glade")
    # builder.connect_signals(Handler())
    # window = builder.get_object('MainWindow')
    # window.show_all()

    num_covers = 5

    i = 0
    covers = []
    for cover in each_cover('/media/josh/Music'):
        covers.append(cover)
        i += 1
        if i == num_covers:
            break
    print(covers)
    mpdclient = nmpd.Mpd('localhost', 6600)
    mpdclient.connect()

    album_cache = nmcache.AlbumCache()
    mpdclient.populate_cache(album_cache)

    def check_status():
        print("Checking status...")

    timer = threading.Timer(1, check_status)
    timer.start()

    win = MyWindow(mpdclient, covers, album_cache)
    win.connect('destroy', Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1:])
