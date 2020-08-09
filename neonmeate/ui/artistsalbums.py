from gi.repository import GdkPixbuf, GObject, Gtk, GLib

from neonmeate.ui import toolkit
from neonmeate.ui.toolkit import gtk_main


# noinspection PyArgumentList,PyUnresolvedReferences
class ArtistsAlbums(Gtk.Frame):
    AlbumWidthPx = 200
    AlbumSpacing = 20

    def __init__(self, mpdclient, art_cache, cfg):
        super(ArtistsAlbums, self).__init__()
        album_width_px = ArtistsAlbums.AlbumWidthPx
        album_spacing = ArtistsAlbums.AlbumSpacing
        self._mpdclient = mpdclient
        self._art_cache = art_cache
        self._cfg = cfg
        self._panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._artists_scrollable = Artists(mpdclient, art_cache)
        self._albums_songs = AlbumsSongs(self._mpdclient, self._art_cache, album_width_px, album_spacing)
        self._panes.pack1(self._artists_scrollable)
        self._panes.pack2(self._albums_songs)
        self._panes.set_position(280)
        self.add(self._panes)
        self._artists_scrollable.connect('artist-selected', self._on_artist_clicked)

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
    def __init__(self, mpdclient, art_cache, album_width_pix, album_spacing):
        super(Albums, self).__init__()
        self._album_width_px = album_width_pix
        self._album_spacing = album_spacing
        self._art_cache = art_cache
        self._mpdclient = mpdclient
        self._albums = toolkit.Column(False)
        self.add_content(self._albums)
        self._selected_artist = None
        self._entries = []

    def _on_art_ready(self, pixbuf, album_count):
        album, count = album_count
        if self._selected_artist != album.artist.name:
            return

        album_entry = AlbumEntry(album, pixbuf, self._album_width_px, self._album_spacing)
        self._entries.append(album_entry)
        if len(self._entries) == count:
            self._on_all_albums_ready()

    def _on_all_albums_ready(self):
        chrono_order = sorted(self._entries, key=lambda e: e.album.date)
        for entry in chrono_order:
            entry.show()
            self._albums.add(entry)
        self.queue_draw()

    def _clear_albums(self):
        self._entries.clear()
        for c in self._albums.get_children():
            self._albums.remove(c)

    def on_artist_selected(self, artist_name, albums):
        if artist_name == '' or self._selected_artist == artist_name:
            return

        self._clear_albums()
        self._selected_artist = artist_name

        for album in albums:
            cover_path = self._art_cache.resolve_cover_file(album.dirpath)
            if cover_path:
                self._art_cache.fetch(cover_path, self._on_art_ready, (album, len(albums)))


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumEntry(Gtk.Box):
    def __init__(self, album, pixbuf, width, spacing):
        super(AlbumEntry, self).__init__(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        self.album = album
        pixbuf = pixbuf.scale_simple(width, width, GdkPixbuf.InterpType.BILINEAR)
        img = Gtk.Image.new_from_pixbuf(pixbuf)
        img.show()
        self.pack_start(img, True, False, 5)

        # todo following not needed
        label_txt = f"{album.title} - {album.date}\n"
        for s in album.sorted_songs():
            label_txt += f"{s.number}. {s.title}\n"


class Songs(toolkit.Scrollable):
    def __init__(self):
        super(Songs, self).__init__()


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumsSongs(Gtk.Frame):

    def __init__(self, mpdclient, art_cache, album_width_px, album_spacing):
        super(AlbumsSongs, self).__init__()
        self._mpdclient = mpdclient
        self._art_cache = art_cache
        self._panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._albums = Albums(self._mpdclient, self._art_cache, album_width_px, album_spacing)
        self._songs = Songs()
        self._panes.pack1(self._albums, False, False)
        self._panes.pack2(self._songs, False, False)
        self._panes.set_position(album_spacing * 2 + album_width_px)
        self.add(self._panes)
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
