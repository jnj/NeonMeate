from gi.repository import Gtk

from .cover import CoverWithGradient


# noinspection PyUnresolvedReferences
class NowPlaying(Gtk.Bin):
    def __init__(self, rng, art_cache, executor, cfg):
        super(NowPlaying, self).__init__()
        self._cfg = cfg
        self._rng = rng
        self._executor = executor
        self._art = art_cache
        self._cover_art = None
        self._current = (None, None)
        self._covpath = None
        self._box = Gtk.VBox()
        self.add(self._box)

    def clear(self):
        self._current = (None, None)
        self._clear_art()

    def on_connection_status(self, connected):
        if not connected:
            self.clear()

    def on_playing(self, artist, album, covpath):
        self._covpath = covpath
        if self._current == (artist, album):
            return
        self._clear_art()
        self._current = (artist, album)
        self._art.fetch(covpath, self._on_art_ready, (artist, album, covpath))

    def switch_art(self):
        artist, album = self._current
        self._current = (None, None)
        self.on_playing(artist, album, self._covpath)

    def _clear_art(self):
        if self._cover_art is not None:
            self._cover_art.destroy()
            self._cover_art = None

    def _update_cover(self, pixbuf, artist, album, covpath):
        self._cover_art = CoverWithGradient(
            pixbuf,
            self._rng,
            self._executor,
            self._cfg,
            artist,
            album,
            covpath)
        self._box.pack_start(self._cover_art, True, True, 0)
        self._box.show_all()

    def _on_art_ready(self, pixbuf, artist_album_covpath):
        artist, album, covpath = artist_album_covpath
        if (self._current != (artist, album)) or (self._cover_art is not None):
            return
        self._update_cover(pixbuf, artist, album, covpath)
        self.queue_draw()
