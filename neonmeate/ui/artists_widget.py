import re

from gi.repository import Gtk, GObject

from neonmeate.ui import toolkit
from neonmeate.ui.toolkit import glib_main


class ArtistsWidget(Gtk.VBox):
    __gsignals__ = {
        'artist_selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'artists_loaded': (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, mpdclient):
        super(ArtistsWidget, self).__init__()
        self._artists = Artists(mpdclient)
        self._searchbar = Gtk.ActionBar()
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_has_frame(True)
        self._searchbar.add(self._search_entry)
        self.pack_start(self._searchbar, False, False, 0)
        self.pack_start(self._artists, True, True, 0)
        self._artists.connect('artist_selected', self._on_artist_selected)
        self._artists.connect('artists_loaded', self._on_artists_loaded)
        self._searched_artist = None
        self._search_entry.connect('search-changed', self._on_artist_searched)
        self.show_all()

    def _on_artist_searched(self, search_entry):
        self._artists.set_filter(search_entry.get_text())

    def _on_artists_loaded(self, _, b):
        self.emit('artists_loaded', b)

    def _on_artist_selected(self, _, artist):
        self.emit('artist_selected', artist)

    def reload_artists(self):
        self._artists.reload_artists()

    def get_artists(self):
        return self._artists.get_artists()

    def clear(self):
        self._artists.clear()


class Artists(Gtk.ScrolledWindow):
    __gsignals__ = {
        'artist_selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'artists_loaded': (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, mpdclient):
        super(Artists, self).__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_shadow_type(Gtk.ShadowType.NONE)
        self._artist_column = toolkit.Column(vmargin=15, selectable_rows=True)
        self.add(self._artist_column)
        self._mpd = mpdclient
        self._artist_column.connect('value-selected', self._on_artist_clicked)
        self._artists = []
        self.reload_artists()

    def get_artists(self):
        return self._artists

    def clear(self):
        self._artists.clear()
        self._artist_column.clear()

    def reload_artists(self):
        self.clear()

        @glib_main
        def on_artists(artists):
            self._artists.extend(artists)
            for artist in self._artists:
                self._artist_column.add_row(artist.name)
            self.emit('artists_loaded', True)

        self._mpd.find_artists(on_artists)

    def _on_artist_clicked(self, obj, value):
        self.emit('artist_selected', value)

    def set_filter(self, artist_text):
        if artist_text is None or len(artist_text) == 0:
            self._artist_column.set_filter_func(None)
            return

        search_txt = artist_text.lower()
        terms = search_txt.split()
        expr = '.*' + '.*'.join([t for t in terms]) + '.*'
        regex = re.compile(expr)

        self._artist_column.invalidate_filter()

        def filter_fn(listboxrow):
            label = listboxrow.get_child()
            txt = label.get_text().lower()
            return regex.search(txt) is not None

        self._artist_column.set_filter_func(filter_fn)