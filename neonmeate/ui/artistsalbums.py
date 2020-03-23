import os

from gi.repository import GdkPixbuf, GObject, Gtk, GLib

from neonmeate.ui import toolkit


class ArtistsAlbums(Gtk.Frame):
    def __init__(self, mpdclient, art_cache):
        super(ArtistsAlbums, self).__init__()
        self._mpdclient = mpdclient
        self._art_cache = art_cache
        self._panes = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self._artists_scrollable = Artists(mpdclient, art_cache)
        self._albums = Albums(self._mpdclient, self._art_cache)
        self._panes.pack1(self._artists_scrollable)
        self._panes.pack2(self._albums)
        self._panes.set_position(280)
        self.add(self._panes)
        self._artists_scrollable.connect('artist-selected', self._on_artist_clicked)

    def _on_artist_clicked(self, column_widget, selected_value):
        self._albums.on_artist_selected(selected_value)


class Artists(toolkit.Scrollable):
    __gsignals__ = {
        'artist-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self, mpdclient, art_cache):
        super(Artists, self).__init__()
        self._artist_column = toolkit.Column(vmargin=10, selectable_rows=True)
        self.add_content(self._artist_column)
        self._mpd = mpdclient

        def on_artists(artists):
            for artist in artists:
                self._artist_column.add_row(artist.name)

        def on_main(artists):
            GLib.idle_add(on_artists, artists)

        self._mpd.find_artists(on_main)
        self._artist_column.connect('value-selected', self._on_artist_clicked)

    def _on_artist_clicked(self, obj, value):
        self.emit('artist-selected', value)


class Albums(toolkit.Scrollable):
    def __init__(self, mpdclient, art_cache):
        super(Albums, self).__init__()
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

        album_entry = AlbumEntry(album, pixbuf)
        self._entries.append(album_entry)
        if len(self._entries) == count:
            self._on_all_albums_ready()

    def _on_all_albums_ready(self):
        chrono_order = sorted(self._entries, key=lambda entry: entry.album.date)
        for entry in chrono_order:
            entry.show()
            self._albums.add(entry)
        self.queue_draw()

    def _clear_albums(self):
        self._entries.clear()
        for c in self._albums.get_children():
            self._albums.remove(c)

    def on_artist_selected(self, artist_name):
        if artist_name == '':
            return
        self._clear_albums()
        self._selected_artist = artist_name

        def on_albums(albums):
            for album in albums:
                cover_path = self._art_cache.resolve_cover_file(album.dirpath)
                if cover_path:
                    self._art_cache.fetch(cover_path, self._on_art_ready, (album, len(albums)))

        def on_main(albums):
            GLib.idle_add(on_albums, albums)

        self._mpdclient.find_albums(artist_name, on_main)


class AlbumEntry(Gtk.Grid):
    def __init__(self, album, pixbuf):
        super(AlbumEntry, self).__init__()
        self.album = album
        self.set_column_spacing(10)
        pixbuf = pixbuf.scale_simple(200, 200, GdkPixbuf.InterpType.BILINEAR)
        img = Gtk.Image.new_from_pixbuf(pixbuf)
        img.show()
        self.attach(img, 0, 0, 1, 1)
        label_txt = f"{album.title} - {album.date}\n"
        for s in album.sorted_songs():
            label_txt += f"{s.number}. {s.title}\n"
        label = Gtk.Label(label_txt)
        label.show()
        self.attach(label, 1, 0, 1, 1)
        self.set_row_baseline_position(0, Gtk.BaselinePosition.TOP)
