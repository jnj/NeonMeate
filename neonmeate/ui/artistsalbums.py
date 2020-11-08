import functools

from gi.repository import GdkPixbuf, GObject, Gtk, GLib

from neonmeate.ui import toolkit
from neonmeate.ui.toolkit import gtk_main, AlbumArt


class AlbumViewOptions:
    def __init__(self):
        self.num_grid_cols = -1
        self.col_spacing = 20
        self.row_spacing = 20
        self.album_size = 150


# noinspection PyArgumentList,PyUnresolvedReferences
class ArtistsAlbums(Gtk.Frame):

    def __init__(self, mpdclient, art_cache, cfg):
        super(ArtistsAlbums, self).__init__()
        album_view_opts = AlbumViewOptions()
        self._album_placeholder_pixbuf = Gtk.IconTheme.get_default().load_icon(
            'music-app', album_view_opts.album_size, 0)
        self._mpdclient = mpdclient
        self._art_cache = art_cache
        self._cfg = cfg
        self._panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._artists_scrollable = Artists(mpdclient, art_cache)

        self._albums_songs = AlbumsSongs(self._mpdclient, self._art_cache,
                                         self._album_placeholder_pixbuf,
                                         album_view_opts)
        self._panes.pack1(self._artists_scrollable)
        self._panes.pack2(self._albums_songs)
        self._panes.set_position(280)
        self.add(self._panes)
        self._artists_scrollable.connect('artist-selected',
                                         self._on_artist_clicked)

    def _on_artist_clicked(self, column_widget, selected_value):
        self._albums_songs.on_artist_selected(selected_value)


# noinspection PyArgumentList,PyUnresolvedReferences
class Artists(toolkit.Scrollable):
    __gsignals__ = {
        'artist-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self, mpdclient, art_cache):
        super(Artists, self).__init__()
        self._artist_column = toolkit.Column(vmargin=15, selectable_rows=True)
        self.add_content(self._artist_column)
        self._mpd = mpdclient

        @gtk_main
        def on_artists(artists):
            for artist in artists:
                self._artist_column.add_row(artist.name)

        self._mpd.find_artists(on_artists)
        self._artist_column.connect('value-selected', self._on_artist_clicked)

    def _on_artist_clicked(self, obj, value):
        self.emit('artist-selected', value)


# noinspection PyArgumentList,PyUnresolvedReferences
class Albums(toolkit.Scrollable):
    def __init__(self, mpdclient, art_cache, placeholder_pixbuf, options):
        super(Albums, self).__init__()
        self._placeholder_pixbuf = placeholder_pixbuf
        self._album_width_px = options.album_size
        self._album_spacing = options.col_spacing
        self._art_cache = art_cache
        self._mpdclient = mpdclient
        self._options = options

        self._albums_grid = Gtk.FlowBox()
        self._albums_grid.set_homogeneous(True)
        self._albums_grid.set_valign(Gtk.Align.START)
        self._albums_grid.set_halign(Gtk.Align.START)
        self._albums_grid.set_selection_mode(Gtk.SelectionMode.SINGLE)

        if options.num_grid_cols > 0:
            self._albums_grid.set_min_children_per_line(options.num_grid_cols)
            self._albums_grid.set_max_children_per_line(options.num_grid_cols)

        self._albums_grid.set_column_spacing(options.col_spacing)
        self._albums_grid.set_row_spacing(options.col_spacing)
        self.add_content(self._albums_grid)
        self._selected_artist = None
        self._entries = []

    def _on_all_albums_ready(self):
        chrono_order = sorted(self._entries, key=lambda e: e.album.date)
        for entry in chrono_order:
            entry.show()
            self._albums_grid.add(entry)
        self.queue_draw()

    def _clear_albums(self):
        self._entries.clear()
        for c in self._albums_grid.get_children():
            self._albums_grid.remove(c)

    def on_artist_selected(self, artist_name, albums):
        if artist_name == '' or self._selected_artist == artist_name:
            return
        self._clear_albums()
        self._selected_artist = artist_name

        for i, album in enumerate(albums):
            album_art = AlbumArt(self._art_cache, album, self._placeholder_pixbuf)
            album_entry = AlbumEntry(i, album, album_art, self._album_width_px, self._album_spacing)
            self._entries.append(album_entry)

        self._on_all_albums_ready()


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumEntry(Gtk.Box):
    def __init__(self, index, album, art, width, spacing):
        super(AlbumEntry, self).__init__(orientation=Gtk.Orientation.VERTICAL,
                                         spacing=spacing)
        self.index = index
        self.width = width
        self.album = album
        self.set_halign(Gtk.Align.START)
        self.img = None
        self._art = art
        self.update_art()

        def _on_done(new_pixbuf, _):
            self.update_art()

        art.resolve(_on_done, None)

    def update_art(self):
        if self.img:
            self.remove(self.img)
        new_pixbuf = self._art.get_scaled_pixbuf(self.width)
        self.img = Gtk.Image.new_from_pixbuf(new_pixbuf)
        self.img.show()
        self.pack_start(self.img, False, False, 0)
        self.queue_draw()

    def __str__(self):
        return self.album


class Songs(toolkit.Scrollable):
    def __init__(self):
        super(Songs, self).__init__()


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumsSongs(Gtk.Frame):

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf, albums_view_options):
        super(AlbumsSongs, self).__init__()
        self._mpdclient = mpdclient
        self._art_cache = art_cache

        self._albums = Albums(
            self._mpdclient,
            self._art_cache,
            placeholder_pixbuf,
            albums_view_options)

        self.add(self._albums)
        self._albums_list = []
        self._selected_artist = None

    def on_artist_selected(self, artist_name):
        if not artist_name or artist_name == self._selected_artist:
            return

        @gtk_main
        def on_albums(albums):
            self._albums_list.clear()
            self._albums_list.extend(albums)
            self._selected_artist = artist_name
            self._albums.on_artist_selected(artist_name, albums)

        self._mpdclient.find_albums(artist_name, on_albums)
