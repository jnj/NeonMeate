from gi.repository import GObject, Gtk, GLib, Pango

import re

from neonmeate.ui import toolkit, controls
from neonmeate.ui.toolkit import glib_main, AlbumArt, TimedInfoBar


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
class ArtistsAlbums(Gtk.VBox):

    def __init__(self, mpdclient, art, cfg):
        super(ArtistsAlbums, self).__init__()
        album_view_opts = AlbumViewOptions()
        self._infobar = TimedInfoBar()
        self.pack_start(self._infobar, False, False, 0);
        self._update_pending = DiffableBoolean()
        self._album_placeholder_pixbuf = \
            Gtk.IconTheme.get_default().load_icon_for_scale(
                'image-missing', album_view_opts.album_size, 1, 0)
        self._art = art
        self._cfg = cfg
        self._mpdclient = mpdclient
        columns = Gtk.HBox()
        self._artists = ArtistsContainer(mpdclient)
        self._artists.connect('artist_selected', self._on_artist_clicked)
        self._artists.connect('artists_loaded', self._on_artists_loaded)
        columns.pack_start(self._artists, False, False, 0)

        self._albums_songs = AlbumsAndSongs(
            self._mpdclient,
            self._art,
            self._album_placeholder_pixbuf,
            album_view_opts
        )
        self._albums_songs.connect('playlist-modified', self._on_playlist_mod)
        columns.pack_end(self._albums_songs, True, True, 0)
        self.pack_end(columns, True, True, 0)
        self.show_all()

    def on_random_fill(self):
        songs = self._mpdclient.get_random(50)

    def _on_playlist_mod(self, widget):
        self._infobar.temp_reveal("Playlist updated")

    def _on_artists_loaded(self, _, done):
        if done:
            self._albums_songs.set_artists(self._artists.get_artists())

    def on_mpd_connected(self, connected):
        if connected:
            self._reload()
        if not connected:
            self._artists.clear()
            self._albums_songs.clear()

    def on_db_update(self, is_updating):
        pending = self._update_pending.current()
        changed = self._update_pending.update(is_updating)
        if pending and changed:
            self._reload()

    def _reload(self):
        self._artists.reload_artists()
        self._albums_songs.reload()

    def _on_artist_clicked(self, col_widget, selected_value):
        self._albums_songs.on_artist_selected(selected_value)


# noinspection PyArgumentList,PyUnresolvedReferences
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


# noinspection PyArgumentList,PyUnresolvedReferences
class Albums(toolkit.Scrollable):
    __gsignals__ = {
        'album-selected': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    @staticmethod
    def album_sort_key(album_entry):
        album = album_entry.album
        return album.date, album.title, album.artist

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf, options):
        super(Albums, self).__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        border_width = 5
        self.set_border_width(border_width)
        self._placeholder_pixbuf = placeholder_pixbuf
        self._album_width_px = options.album_size
        self._max_width = self._album_width_px + 20 + border_width
        self._album_spacing = options.col_spacing
        self._art = art_cache
        self._mpdclient = mpdclient
        self._options = options
        self._albums_column = Gtk.VBox()
        self._albums_column.set_valign(Gtk.Align.START)
        self._albums_column.set_halign(Gtk.Align.START)
        self._albums_column.set_homogeneous(True)
        self.add_content(self._albums_column)
        self._selected_artist = None
        self._selected_album = None
        self._entries = []
        self.show_all()
        self._artists = []

    def do_get_preferred_width(self):
        return self._max_width, self._max_width

    def set_artists(self, artists):
        self._selected_artist = None
        self._artists.clear()
        self._artists.extend(artists)

    def on_reload(self):
        self.clear()

    def clear(self):
        self._clear_albums()

    def get_selected_album(self):
        return self._selected_album

    def _on_album_selected(self, entry, index):
        self._selected_album = entry.album
        self.emit('album-selected', index)

    def _on_all_albums_ready(self):
        for i, entry in enumerate(self._entries):
            entry.show()
            self._albums_column.add(entry)
            entry.connect('clicked', self._on_album_selected, i)
        self.queue_draw()

    def _clear_albums(self):
        self._selected_artist = None
        self._selected_album = None
        self._entries.clear()
        for c in self._albums_column.get_children():
            c.destroy()

    def on_artist_selected(self, artist_name, albums):
        if not artist_name or self._selected_artist == artist_name:
            return

        self._clear_albums()
        self._selected_artist = artist_name
        spacing = self._album_spacing
        entries = []

        for i, album in enumerate(albums):
            aa = AlbumArt(self._art, album, self._placeholder_pixbuf)
            entry = AlbumEntry(i, album, aa, self._album_width_px, spacing,
                               self._mpdclient)
            entries.append(entry)

        self._entries = sorted(entries, key=Albums.album_sort_key)
        self._on_all_albums_ready()


# noinspection PyArgumentList,PyUnresolvedReferences
class FixedWidth(Gtk.Bin):
    def __init__(self, max_width):
        super(FixedWidth, self).__init__()
        self._max_width = max_width

    def do_get_preferred_width(self):
        child = self.get_child()
        if child:
            t = (1, 1)
            minw, nat = Gtk.Widget.do_get_preferred_width(child)
            return min(minw, self._max_width), min(nat, self._max_width)
        return self._max_width, self._max_width


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumEntry(Gtk.Box):
    __gsignals__ = {
        'clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, index, album, art, width, spacing, mpdclient):
        super(AlbumEntry, self).__init__(spacing=spacing)
        self._mpdclient = mpdclient
        self._btn = Gtk.Button()
        self._btn.set_relief(Gtk.ReliefStyle.NONE)
        self._btn.set_always_show_image(True)
        esc_title = GLib.markup_escape_text(album.title)
        esc_path = GLib.markup_escape_text(album.dirpath)
        self._btn.set_tooltip_markup(
            f'{esc_title}\n<small>{album.date}\n{esc_path}</small>')
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

    def _on_right_click(self, x):
        print('right clicked')

    def _img_clicked(self, x):
        self.emit('clicked')

    def _update_art(self):
        if self._img:
            self._btn.set_image(None)
        new_pixbuf = self._art.get_scaled_pixbuf(self.width)
        self._img = Gtk.Image.new_from_pixbuf(new_pixbuf)
        if self._img:
            self._btn.set_image(self._img)
            self.queue_draw()

    def __str__(self):
        return self.album


# noinspection PyArgumentList,PyUnresolvedReferences
class Songs(Gtk.ScrolledWindow):
    def __init__(self, album):
        super(Songs, self).__init__()
        self._album = album
        self._box = toolkit.Column(15, True, True)
        self.add(self._box)
        self._songs = album.sorted_songs()

        # todo bind model

        def fmt_number(n):
            if len(self._songs) < 100:
                return f'{n:02}'
            else:
                return f'{n:03}'

        for song in self._songs:
            trackno = fmt_number(song.number)
            if song.is_compilation_track():
                text = f'{trackno}. {song.artist} - {song.title}'
            else:
                text = f'{trackno}. {song.title}'
            self._box.add_row(text)

        self.show_all()

    def for_each_selected_song(self, fn):
        def callback(box, row, *data):
            i = row.get_index()
            song = self._songs[i]
            fn(song)

        rows = self._box.get_selected_rows()
        for row in rows:
            callback(self._box, row)
        del rows


# noinspection PyArgumentList,PyUnresolvedReferences
class ExpandedButtonBox(Gtk.HButtonBox):
    def __init__(self):
        super(ExpandedButtonBox, self).__init__()
        self.set_layout(Gtk.ButtonBoxStyle.EXPAND)

    def add_labeled(self, label_text):
        button = Gtk.Button()
        button.add(Gtk.Label(label_text))
        self.add(button)
        return button


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumsAndSongs(Gtk.HBox):
    __gsignals__ = {
        'playlist-modified': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf,
                 albums_view_options):
        super(AlbumsAndSongs, self).__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._mpdclient = mpdclient
        self._art_cache = art_cache
        self._container = Gtk.HBox()
        self.add(self._container)
        self._albums = Albums(
            self._mpdclient,
            self._art_cache,
            placeholder_pixbuf,
            albums_view_options)
        self._albums.connect('album-selected', self._on_album_selected)
        self._container.pack_start(self._albums, False, True, 0)
        self._songsbox = Gtk.VBox()
        self._container.pack_end(self._songsbox, True, True, 0)
        self._container.add(self._songsbox)
        self._song_action_bar = Gtk.ActionBar()
        self._song_info_bar = Gtk.Label()
        self._song_info_bar.set_justify(Gtk.Justification.CENTER)
        self._song_info_bar.set_line_wrap(True)
        self._song_info_bar.set_padding(10, 10)

        self._all_buttonbox = ExpandedButtonBox()
        self._add_all = self._all_buttonbox.add_labeled('Add all')
        self._rem_all = self._all_buttonbox.add_labeled('Remove all')

        self._sel_buttonbox = ExpandedButtonBox()
        self._add_sel = controls.ControlButton('list-add')
        self._add_sel.set_tooltip_markup('Add selected')
        self._rem_sel = controls.ControlButton('list-remove')
        self._rem_sel.set_tooltip_markup('Remove selected')
        self._sel_buttonbox.add(self._add_sel)
        self._sel_buttonbox.add(self._rem_sel)

        self._song_action_bar.add(self._all_buttonbox)
        self._song_action_bar.add(self._sel_buttonbox)
        self._songsbox.pack_start(self._song_info_bar, False, False, 0)
        self._songsbox.pack_end(self._song_action_bar, False, False, 0)
        self._add_all.connect('clicked', self._on_add_all)
        self._rem_all.connect('clicked', self._on_rem_all)
        self._add_sel.connect('clicked', self._on_add_sel)
        self._rem_sel.connect('clicked', self._on_rem_sel)
        self._albums_list = []
        self._artist_by_name = {}
        self._selected_artist = None
        self._selected_album = None
        self._current_songs = None
        self.show_all()

    def _get_selected_songs(self):
        if self._current_songs:
            songs = []

            def on_song(song):
                songs.append(song)

            self._current_songs.for_each_selected_song(on_song)
            return songs
        return []

    def _on_add_sel(self, btn):
        songs = self._get_selected_songs()
        if songs:
            self._mpdclient.add_songs(songs)
            self.emit('playlist-modified')

    def _on_rem_sel(self, btn):
        songs = self._get_selected_songs()
        if songs:
            self._mpdclient.remove_songs(songs)
            self.emit('playlist-modified')

    def _on_add_all(self, btn):
        if self._selected_album:
            self._mpdclient.add_album_to_playlist(self._selected_album)
            self.emit('playlist-modified')

    def _on_rem_all(self, btn):
        if self._selected_album:
            self._mpdclient.remove_album_from_playlist(self._selected_album)
            self.emit('playlist-modified')

    def _on_album_selected(self, albums, index):
        album = albums.get_selected_album()
        self._selected_album = album
        self._update_song_info()
        self.clear_songs()
        self._current_songs = Songs(album)
        self._current_songs.show()
        self._songsbox.pack_end(self._current_songs, True, True, 0)
        self.queue_draw()

    def _update_song_info(self):
        title = GLib.markup_escape_text(self._selected_album.title)
        year = GLib.markup_escape_text(str(self._selected_album.date))
        self._song_info_bar.set_markup(
            f'<b><big>{title}</big></b>\n<small>{year}</small>')

    def clear_songs(self):
        for c in self._songsbox.get_children():
            if c != self._song_action_bar and c != self._song_info_bar:
                c.destroy()

    def clear(self):
        self._song_info_bar.set_markup('')
        self._albums.clear()
        self.clear_songs()
        self._selected_artist = None
        self._selected_album = None

    def set_artists(self, artists):
        self._albums.set_artists(artists)
        self._artist_by_name = {a.name: a for a in artists}

    def reload(self):
        pass

    def on_artist_selected(self, artist_name):
        if not artist_name or artist_name == self._selected_artist:
            return
        self._selected_artist = None
        self._selected_album = None
        self._current_songs = None
        self.clear_songs()
        self._song_info_bar.set_markup('')
        artist_inst = self._artist_by_name[artist_name]

        @glib_main
        def on_albums(albums):
            self._albums_list.clear()
            self._albums_list.extend(albums)
            self._selected_artist = artist_name
            self._albums.on_artist_selected(artist_name, albums)

        self._mpdclient.find_albums(artist_inst, on_albums)


# noinspection PyArgumentList,PyUnresolvedReferences
class ArtistsContainer(Gtk.HBox):
    __gsignals__ = {
        'artist_selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'artists_loaded': (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, mpdclient):
        super(ArtistsContainer, self).__init__()
        # super(ArtistsContainer, self).set_preferred_size(300, -1)
        self._vbox = Gtk.VBox()
        self.add(self._vbox)
        self._artists = Artists(mpdclient)
        self._searchbar = Gtk.ActionBar()
        self._search_entry = Gtk.SearchEntry()
        self._searchbar.add(self._search_entry)
        self._vbox.pack_start(self._searchbar, False, False, 0)
        self._vbox.pack_start(self._artists, True, True, 0)
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
