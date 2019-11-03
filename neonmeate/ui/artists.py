import os

from gi.repository import GdkPixbuf, GObject, Gtk

from neonmeate.ui import toolkit


class Artists(Gtk.Frame):
    __gsignals__ = {
        'artist-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self, album_cache, art_cache):
        super(Artists, self).__init__()
        self._album_cache = album_cache
        self._art_cache = art_cache
        self._panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._artist_list = toolkit.Column()
        self._artists_scrollable = toolkit.Scrollable()
        self._artists_scrollable.add_content(self._artist_list)
        self._albums = Albums(self._album_cache, self._art_cache)
        self._panes.pack1(self._artists_scrollable)
        self._panes.pack2(self._albums)
        self._panes.set_position(400)
        self.add(self._panes)
        self._artist_list.connect('value-selected', self._on_artist_clicked)

        for artist in self._album_cache.all_artists():
            self._add_artist(artist)

    def _add_artist(self, name):
        self._artist_list.add_row(name)

    def _on_artist_clicked(self, column_widget, selected_value):
        self._albums.on_artist_selected(selected_value)


class Albums(toolkit.Scrollable):
    def __init__(self, album_cache, art_cache):
        super(Albums, self).__init__()
        self._art_cache = art_cache
        self._album_cache = album_cache
        self._albums = toolkit.Column()
        self.add_content(self._albums)

    def _on_art_ready(self, pixbuf):
        pixbuf = pixbuf.scale_simple(400, 400, GdkPixbuf.InterpType.BILINEAR)
        img = Gtk.Image.new_from_pixbuf(pixbuf)
        img.show()
        self._albums.add(img)
        self.queue_draw()

    def _clear_albums(self):
        for c in self._albums.get_children():
            self._albums.remove(c)

    def on_artist_selected(self, artist_name):
        self._clear_albums()
        albums = self._album_cache.get_albums(artist_name)
        for album in albums:
            cover_path = self._album_cache.cover_art_path(artist_name, album)
            if cover_path and os.path.exists(cover_path):
                self._art_cache.fetch(cover_path, self._on_art_ready, (artist_name, album))
