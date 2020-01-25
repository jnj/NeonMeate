import os

from gi.repository import GdkPixbuf, GObject, Gtk

from neonmeate.ui import toolkit


class NowPlaying(Gtk.Frame):
    def __init__(self, album_cache, art_cache):
        super(Gtk.Frame, self).__init__()
        self._album_cache = album_cache
        self._art_cache = art_cache
        print(f"window has dimensions {self.get_allocated_width()} by {self.get_allocated_height()}")

