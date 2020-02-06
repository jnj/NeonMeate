import os

from gi.repository import GdkPixbuf, GObject, Gtk

from neonmeate.ui import toolkit
from .cover import CoverWithGradient


class NowPlaying(Gtk.Frame):
    def __init__(self, album_cache, art_cache):
        super(Gtk.Frame, self).__init__()
        self._album_cache = album_cache
        self._art_cache = art_cache
        self._cover_art = None
        self._current = (None, None)

    def clear(self):
        self._current = (None, None)
        self._clear_art()

    def on_playing(self, artist, album, covpath):
        if self._current == (artist, album):
            return
        self._clear_art()
        self._current = (artist, album)
        self._art_cache.fetch(covpath, self._on_art_ready, (artist, album))

    def _clear_art(self):
        if self._cover_art is not None:
            self.remove(self._cover_art)

    def _on_art_ready(self, pixbuf, album_artist):
        if self._current == album_artist:
            self._cover_art = CoverWithGradient(pixbuf)
            self._cover_art.show()
            self.add(self._cover_art)
            self.queue_draw()
