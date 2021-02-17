from gi.repository import GObject, Gtk, GLib

from neonmeate.ui import toolkit, controls
from neonmeate.ui.toolkit import gtk_main, AlbumArt


class DiffableBoolean:
    def __init__(self):
        self.value = False

    def current(self):
        return self.value

    def update(self, new_value):
        changed = new_value != self.value
        self.value = new_value
        return changed


class AlbumViewOptions:
    def __init__(self):
        self.num_grid_cols = 1
        self.album_size = 300
        self.col_spacing = 30
        self.row_spacing = 30


# noinspection PyArgumentList,PyUnresolvedReferences
class ArtistsAlbums(Gtk.Frame):

    def __init__(self, mpdclient, art, cfg):
        super(ArtistsAlbums, self).__init__()
        album_view_opts = AlbumViewOptions()
        artist_list_position = 280
        album_view_opts.album_size = 800 - artist_list_position - 40
        self._update_pending = DiffableBoolean()
        self._album_placeholder_pixbuf = \
            Gtk.IconTheme.get_default().load_icon_for_scale(
                'emblem-music-symbolic', album_view_opts.album_size, 1, 0)
        self._art = art
        self._cfg = cfg
        self._mpdclient = mpdclient
        self._panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._artists_scrollable = Artists(mpdclient, art)

        self._albums_songs = AlbumsPane(
            self._mpdclient,
            self._art,
            self._album_placeholder_pixbuf,
            album_view_opts
        )

        self._panes.pack1(self._artists_scrollable)
        self._panes.pack2(self._albums_songs)

        self._panes.set_position(artist_list_position)
        self.add(self._panes)
        self._artists_scrollable.connect(
            'artist-selected', self._on_artist_clicked
        )

    def on_db_update(self, is_updating):
        pending = self._update_pending.current()
        changed = self._update_pending.update(is_updating)
        if pending and changed:
            self._reload()

    def _reload(self):
        self._artists_scrollable.reload_artists()
        self._albums_songs.reload()

    def _on_artist_clicked(self, col_widget, selected_value):
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
        self._artist_column.connect('value-selected', self._on_artist_clicked)
        self.reload_artists()

    def reload_artists(self):
        self._artist_column.clear()

        @gtk_main
        def on_artists(artists):
            for artist in artists:
                self._artist_column.add_row(artist.name)

        self._mpd.find_artists(on_artists)

    def _on_artist_clicked(self, obj, value):
        self.emit('artist-selected', value)


# noinspection PyArgumentList,PyUnresolvedReferences
class Albums(toolkit.Scrollable):
    def __init__(self, mpdclient, art_cache, placeholder_pixbuf, options):
        super(Albums, self).__init__()
        self.set_border_width(5)
        self._placeholder_pixbuf = placeholder_pixbuf
        self._album_width_px = options.album_size
        self._album_spacing = options.col_spacing
        self._art = art_cache
        self._mpdclient = mpdclient
        self._options = options
        self._albums_grid = Gtk.FlowBox()
        self._albums_grid.set_orientation(Gtk.Orientation.HORIZONTAL)
        self._albums_grid.set_max_children_per_line(30)
        self._albums_grid.set_valign(Gtk.Align.START)
        self._albums_grid.set_halign(Gtk.Align.START)
        self._albums_grid.set_homogeneous(True)
        self.add_content(self._albums_grid)
        self._selected_artist = None
        self._entries = []
        self.show_all()

    def on_reload(self):
        pass

    def _on_all_albums_ready(self):
        chrono_order = sorted(self._entries, key=lambda e: e.album.date)
        for _, entry in enumerate(chrono_order):
            entry.show()
            self._albums_grid.add(entry)
        self.queue_draw()

    def _clear_albums(self):
        self._entries.clear()
        for c in self._albums_grid.get_children():
            self._albums_grid.remove(c)

    def on_artist_selected(self, artist_name, albums):
        if not artist_name or self._selected_artist == artist_name:
            return

        self._clear_albums()
        self._selected_artist = artist_name
        spacing = self._album_spacing

        for i, album in enumerate(albums):
            aa = AlbumArt(self._art, album, self._placeholder_pixbuf)
            entry = AlbumEntry(i, album, aa, self._album_width_px, spacing,
                               self._mpdclient)
            self._entries.append(entry)

        self._on_all_albums_ready()


# noinspection PyUnresolvedReferences
class AddRemove(Gtk.Popover):
    __gsignals__ = {
        'add-clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'remove-clicked': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, artist, album, parent_widget):
        super(AddRemove, self).__init__()
        self._artist = artist
        self._album = album
        self._vbox = Gtk.VBox()
        self._add_btn = controls.ControlButton('list-add')
        self._rem_btn = controls.ControlButton('list-remove')
        self._vbox.pack_start(self._add_btn, False, False, 0)
        self._vbox.pack_start(self._rem_btn, False, False, 0)
        self.add(self._vbox)
        self._vbox.show_all()
        self.set_relative_to(parent_widget)
        self._add_btn.connect('clicked', self._on_add)
        self._rem_btn.connect('clicked', self._on_rem)

    def _on_add(self, x):
        self.emit('add-clicked')

    def _on_rem(self, x):
        self.emit('remove-clicked')


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumEntry(Gtk.VBox):

    def __init__(self, index, album, art, width, spacing, mpdclient):
        super(AlbumEntry, self).__init__(spacing=spacing)
        self._mpdclient = mpdclient
        self._btn = Gtk.Button()
        self._btn.set_relief(Gtk.ReliefStyle.NONE)
        self._btn.set_always_show_image(True)
        esc_title = GLib.markup_escape_text(album.title)
        self._btn.set_tooltip_markup(
            f'{esc_title}\n<small>{album.date}</small>')
        self._popover = AddRemove('', album, self)
        self._popover.connect('add-clicked', self._on_add)
        self._popover.connect('remove-clicked', self._on_remove)
        self.index = index
        self.width = width
        self.album = album
        self.set_halign(Gtk.Align.START)
        self._img = None
        self._art = art
        self._update_art()
        self.add(self._btn)
        self._btn.show()
        self._btn.connect('clicked', self._img_clicked)

        def _on_done(new_pixbuf, _):
            self._update_art()

        art.resolve(_on_done, None)

    def _on_add(self, x):
        self._mpdclient.add_album_to_playlist(self.album)

    def _on_remove(self, x):
        self._mpdclient.remove_album_from_playlist(self.album)

    def _img_clicked(self, x):
        self._popover.popup()

    def _update_art(self):
        if self._img:
            self._btn.set_image(None)
            # self.remove(self._label)
        new_pixbuf = self._art.get_scaled_pixbuf(self.width)
        self._img = Gtk.Image.new_from_pixbuf(new_pixbuf)
        if self._img:
            self._btn.set_image(self._img)
            self.queue_draw()

    def __str__(self):
        return self.album


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumsPane(Gtk.Frame):

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf,
                 albums_view_options):
        super(AlbumsPane, self).__init__()
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

    def reload(self):
        pass

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
