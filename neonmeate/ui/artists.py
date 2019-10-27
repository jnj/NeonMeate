from neonmeate.ui import toolkit
from gi.repository import GObject, Gtk


class Artists(Gtk.Frame):
    __gsignals__ = {
        'artist-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self, album_cache):
        super(Artists, self).__init__()
        self._album_cache = album_cache
        self._panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._artist_list = toolkit.Column()
        self._artists_scrollable = toolkit.Scrollable()
        self._artists_scrollable.add_content(self._artist_list)
        self._panes.pack1(self._artists_scrollable)
        self._albums = Albums(self._album_cache)
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
        return True


class Albums(Gtk.Frame):
    def __init__(self, album_cache):
        super(Albums, self).__init__()
        self._album_cache = album_cache
        self._albums_scrollable = toolkit.Scrollable()
        self._flow = Gtk.FlowBox()
        self._albums_scrollable.add_content(self._flow)

    def on_artist_selected(self, artist_name):
        albums = self._album_cache.get_albums(artist_name)
        # todo load covers into flowbox...
