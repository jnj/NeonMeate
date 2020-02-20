from gi.repository import Gtk

from .cover import CoverWithGradient


# noinspection PyUnresolvedReferences
class NowPlaying(Gtk.Frame):
    def __init__(self, rng, art_cache, executor):
        super(Gtk.Frame, self).__init__()
        self._rng = rng
        self._executor = executor
        self._art_cache = art_cache
        self._cover_art = None
        self._current = (None, None)
        self._box = Gtk.VBox()
        self.add(self._box)

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
            self._cover_art.destroy()
            self._cover_art = None

    def _on_art_ready(self, pixbuf, album_artist):
        if self._current == album_artist and self._cover_art is None:
            self._cover_art = CoverWithGradient(pixbuf, self._rng, self._executor)
            self._box.pack_start(self._cover_art, True, True, 0)
            self._box.show()
            self._cover_art.show()
            self.queue_draw()
