from gi.repository import GObject, Gtk, GLib, Pango, GdkPixbuf, Gdk

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
        self.album_size = 280
        self.col_spacing = 30
        self.row_spacing = 30


# noinspection PyArgumentList,PyUnresolvedReferences
class ArtistsAlbums(Gtk.VBox):

    def __init__(self, mpdclient, art, cfg):
        super(ArtistsAlbums, self).__init__()
        album_view_opts = AlbumViewOptions()
        self._infobar = TimedInfoBar()
        self.pack_start(self._infobar, False, False, 0)
        self._update_pending = DiffableBoolean()
        self._album_placeholder_pixbuf = \
            Gtk.IconTheme.get_default().load_icon_for_scale(
                'media-optical-cd-audio-symbolic',
                album_view_opts.album_size, 1, 0)
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
        self._mpdclient.get_random(50)

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
class SongsMenu(Gtk.Popover):

    def __init__(self, album, mpdclient):
        super(SongsMenu, self).__init__()
        margin = 12
        row_spacing = 10
        self._selected_songs = []
        self._mpdclient = mpdclient
        self._album = album
        self._scrollable = Gtk.ScrolledWindow()
        self._scrollable.set_propagate_natural_height(True)
        self._scrollable.set_propagate_natural_width(True)
        self._scrollable.set_max_content_width(360)
        self._scrollable.set_max_content_height(400)
        self._scrollable.set_overlay_scrolling(True)
        self._scrollable.set_shadow_type(Gtk.ShadowType.NONE)
        self.add(self._scrollable)
        self._vbox = Gtk.VBox()
        self._vbox.set_halign(Gtk.Align.START)
        self._scrollable.add(self._vbox)
        self._songslist = Gtk.VBox()
        self._songslist.set_spacing(row_spacing)
        self._songslist.set_halign(Gtk.Align.START)
        self._vbox.add(self._songslist)

        self._songslist.set_margin_top(margin)
        self._songslist.set_margin_bottom(margin)
        self._songslist.set_margin_start(margin)
        self._songslist.set_margin_end(margin)
        self._songs = album.sorted_songs()

        for song in self._songs:
            checkbox = Gtk.CheckButton()
            label = Gtk.Label()
            label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            label.set_text(f'{song.zero_padded_number()}. {song.title}')
            label.set_property('xalign', 0)
            checkbox.set_active(True)
            checkbox.add(label)

            # using a default value for the song argument allows
            # us to not close over the 'song' variable, so
            # that within this function its value will be that
            # of the current loop iteration.
            def toggle_handler(button, current_song=song):
                included = current_song in self._selected_songs
                if button.get_active() and not included:
                    self._selected_songs.append(current_song)
                if not button.get_active() and included:
                    self._selected_songs.remove(current_song)
            checkbox.connect('toggled', toggle_handler)

            self._songslist.add(checkbox)
            self._selected_songs.append(song)

        self._btn_box = Gtk.ButtonBox()
        self._btn_box.set_margin_start(margin)
        self._btn_box.set_margin_top(margin)
        self._btn_box.set_margin_bottom(margin)
        self._btn_box.set_margin_end(margin)
        self._btn_box.set_halign(Gtk.Align.START)
        self._btn_box.set_orientation(Gtk.Orientation.VERTICAL)
        self._btn_box.set_spacing(row_spacing)
        self._vbox.add(self._btn_box)
        self._add_all_btn = Gtk.Button()
        label = Gtk.Label()
        label.set_text('Add Selected')
        label.set_xalign(0)
        self._add_all_btn.add(label)
        self._btn_box.add(self._add_all_btn)
        self._scrollable.show_all()

        self._rem_all_btn = Gtk.Button()
        label = Gtk.Label()
        label.set_text('Remove Selected')
        label.set_xalign(0)
        self._rem_all_btn.add(label)
        self._btn_box.add(self._rem_all_btn)
        self._add_all_btn.connect('clicked', self._on_add_sel)
        self._rem_all_btn.connect('clicked', self._on_rem_sel)
        self._scrollable.show_all()

    def _get_selected_songs(self):
        print(f'selected songs:')
        for song in self._selected_songs:
            print(f'{song.zero_padded_number()}. {song.title}\n')
        return self._selected_songs

    def _on_add_sel(self, btn):
        songs = self._get_selected_songs()
        if songs:
            self._mpdclient.add_songs(songs)
            # self.emit('playlist-modified')

    def _on_rem_sel(self, btn):
        songs = self._get_selected_songs()
        if songs:
            self._mpdclient.remove_songs(songs)
            # self.emit('playlist-modified')


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

    def do_get_preferred_width(self):
        w = 240
        return w, w

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
class Albums(Gtk.ScrolledWindow):
    __gsignals__ = {
        'album-selected': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    @staticmethod
    def album_sort_key(album):
        return album.date, album.title, album.artist

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf, options):
        super(Albums, self).__init__()
        self._placeholder_pixbuf = placeholder_pixbuf
        self._album_width_px = options.album_size
        self._album_spacing = options.col_spacing
        self._art = art_cache
        self._mpdclient = mpdclient
        self._options = options
        self._model = Gtk.ListStore(GObject.TYPE_PYOBJECT)
        self._view = Gtk.IconView(self._model)
        self._view.set_hexpand(True)
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.set_has_tooltip(True)
        self._view.connect('query-tooltip', self._on_tooltip)
        self.add(self._view)
        self._surface_cache = {}

        renderer = Gtk.CellRendererPixbuf()
        self._view.pack_start(renderer, False)
        self._placeholder_surface = self.pixbuf_surface(
            self._placeholder_pixbuf)

        def render_cover(view, cell, model, iter, placeholder_pb):
            album = model[iter][0]
            surface = self._surface_cache.get(album, self._placeholder_surface)
            if surface != self._placeholder_surface:
                cell.set_property('surface', surface)
                return
            if album.art is None:
                album.art = AlbumArt(art_cache, album, placeholder_pb)
                row = Gtk.TreeRowReference.new(model, model.get_path(iter))

                def on_art_ready(ready_pb, _):
                    path = row.get_path()
                    if path:
                        model.row_changed(path, model.get_iter(path))
                    self.queue_draw()

                album.art.resolve(on_art_ready, None)
            elif album.art.is_resolved():
                pb = album.art.get_scaled_pixbuf(self._album_width_px)
                surface = self.pixbuf_surface(pb)
                self._surface_cache[album] = surface
            cell.set_property('surface', surface)

        self._view.set_cell_data_func(renderer, render_cover, None)

        def render_album_info(view, cell, model, iter, data):
            album = model[iter][0]
            esc_title = GLib.markup_escape_text(album.title)
            esc_date = GLib.markup_escape_text(str(album.date))
            markup = f'<b>{esc_title}</b>\n<small>{esc_date}</small>'
            cell.set_property('markup', markup)

        txt_render = Gtk.CellRendererText()
        txt_render.set_visible(True)
        txt_render.set_property('alignment', Pango.Alignment.CENTER)
        txt_render.set_property('xalign', 0.5)
        txt_render.set_property('ellipsize', Pango.EllipsizeMode.END)
        self._view.pack_start(txt_render, False)
        self._view.set_cell_data_func(txt_render, render_album_info, None)
        self._view.connect('button-press-event', self._on_right_click)
        self._selected_artist = None
        self._selected_album = None
        self._artists = []
        self.show_all()

    def _on_right_click(self, widget, event):
        path, path_iter = self._get_path_at_position(event, widget)
        if event.button == Gdk.BUTTON_SECONDARY and path:
            popover = SongsMenu(self._model[path_iter][0], self._mpdclient)
            ok, rect = self._view.get_cell_rect(path)
            if ok:
                popover.set_pointing_to(rect)
                popover.set_relative_to(self)
                popover.popup()
                return True
        return False

    def _get_path_at_position(self, event, widget):
        x = int(event.x)
        y = int(event.y)
        path = widget.get_path_at_pos(x, y)
        if path:
            path_iter = self._model.get_iter(path)
            return path, path_iter
        return None, None

    def _on_tooltip(self, widget, x, y, keyboard, tooltip):
        w = self.get_hadjustment().get_value()
        z = self.get_vadjustment().get_value()
        path = widget.get_path_at_pos(int(x + w), int(y + z))
        if path is None:
            return False
        model = widget.get_model()
        iter = model.get_iter(path)
        album = model[iter][0]
        esc = GLib.markup_escape_text(album.dirpath)
        markup = f'{esc}'
        tooltip.set_markup(markup)
        return True

    def pixbuf_surface(self, pixbuf):
        return Gdk.cairo_surface_create_from_pixbuf(
            pixbuf,
            self.get_scale_factor(),
            self.get_window()
        )

    def set_artists(self, artists):
        self._artists.clear()
        self._selected_artist = None
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
        pass
        # for i, entry in enumerate(self._entries):
        #     entry.show()
        #     self._container.add(entry)
        #     entry.connect('clicked', self._on_album_selected, i)
        # self.queue_draw()

    def _clear_albums(self):
        self._selected_artist = None
        self._selected_album = None
        self._model.clear()

    def on_artist_selected(self, artist_name, albums):
        if not artist_name or self._selected_artist == artist_name:
            return
        self._clear_albums()
        self._selected_artist = artist_name
        for album in sorted(list(albums), key=Albums.album_sort_key):
            self._model.append([album])

        # for i, album in enumerate(albums):
        # art = AlbumArt(self._art, album, self._placeholder_pixbuf)
        # entry = AlbumEntry(i, album, art, self._album_width_px, self._mpdclient)
        # entries.append(entry)

        self._on_all_albums_ready()


class AlbumInfoText(Gtk.Box):
    def __init__(self, width):
        super(AlbumInfoText, self).__init__(0)
        self._width = width
        self._label = Gtk.Label()
        # self._label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        self._label.set_line_wrap(True)
        self._label.set_selectable(False)
        self.add(self._label)

    def do_get_preferred_width(self):
        w = self._width + 6
        return w, w

    def set_text(self, txt):
        self._label.set_markup(txt)


class ExpanderFrame(Gtk.Frame):
    def __init__(self, length):
        super(ExpanderFrame, self).__init__()
        self._length = length

    def do_get_preferred_size(self):
        t = (self._length, self._length)
        return t, t


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumThumbnail(Gtk.Box):
    __gsignals__ = {
        'clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, album, art, size):
        super(AlbumThumbnail, self).__init__()
        self._size = size
        self._img = None
        self._art = art
        self._album = album
        self._eventbox = Gtk.EventBox()
        self._eventbox.connect('button-press-event', self._img_clicked)
        self.add(self._eventbox)
        self._update_art()

        def _on_done(new_pixbuf, _):
            self._update_art()

        art.resolve(_on_done, None)

    def do_get_preferred_width_for_height(self, height):
        return (self._size, self._size)

    def do_get_preferred_width(self):
        return (self._size, self._size)

    def do_get_preferred_height(self):
        return (self._size, self._size)

    def do_get_preferred_height_for_width(self, width):
        return (self._size, self._size)

    def _img_clicked(self, x, y):
        self.emit('clicked')

    def _update_art(self):
        if self._img:
            self._img.clear()
        new_pixbuf = self._art.get_scaled_pixbuf(self._size)

        if self._img:
            self._img.set_from_pixbuf(new_pixbuf)
        else:
            self._img = Gtk.Image.new_from_pixbuf(new_pixbuf)
            self._eventbox.add(self._img)

        self.queue_draw()


# noinspection PyArgumentList,PyUnresolvedReferences
class AlbumEntry(Gtk.VBox):
    __gsignals__ = {
        'clicked': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, index, album, art, width, mpdclient):
        super(AlbumEntry, self).__init__()
        self._mpdclient = mpdclient
        self.index = index
        self.width = width
        self.album = album
        self._thumb = AlbumThumbnail(album, art, width)
        self._art = art
        # self._frame = frame
        self.add(self._thumb)
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.set_spacing(0)
        # self._img_event_box.connect('button-press-event', self._img_clicked)

        title = AlbumInfoText(self.width)
        esc_title = GLib.markup_escape_text(album.title)
        esc_date = GLib.markup_escape_text(str(album.date))
        info_markup = f'<b>{esc_title}</b>\n{esc_date}'
        title.set_margin_top(16)
        title.set_halign(Gtk.Align.CENTER)
        title.set_text(info_markup)
        self.add(title)

        # self.set_margin_bottom(48)
        # self._update_art()
        self.show_all()

        # def _on_done(new_pixbuf, _):
        #     self._update_art()
        #
        # art.resolve(_on_done, None)

    def do_get_preferred_width(self):
        return self.width, self.width

    def _on_add(self, x):
        self._mpdclient.add_album_to_playlist(self.album)

    def _on_remove(self, x):
        self._mpdclient.remove_album_from_playlist(self.album)

    def _on_right_click(self, x):
        print('right clicked')

    def _img_clicked(self, x, y):
        self.emit('clicked')

    def _update_art(self):
        if self._img:
            self._img.clear()
        new_pixbuf = self._art.get_scaled_pixbuf(self.width)
        if self._img:
            self._img.set_from_pixbuf(new_pixbuf)
        else:
            self._img = Gtk.Image.new_from_pixbuf(new_pixbuf)
        if self._img:
            if self._frame.get_child() is None:
                self._frame.add(self._img)
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
class AlbumsAndSongs(Gtk.Box):
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

        # self._container = Gtk.HBox()
        # self.add(self._container)

        self._albums = Albums(
            self._mpdclient,
            self._art_cache,
            placeholder_pixbuf,
            albums_view_options)
        self._albums.connect('album-selected', self._on_album_selected)
        self.add(self._albums)

        # self._container.pack_start(self._albums_frame, False, True, 0)
        # self._songsbox = Gtk.VBox()
        # self._container.pack_end(self._songsbox, True, True, 0)
        # self._container.add(self._songsbox)
        # self._song_action_bar = Gtk.ActionBar()
        # self._song_info_bar = Gtk.Label()
        # self._song_info_bar.set_justify(Gtk.Justification.CENTER)
        # self._song_info_bar.set_line_wrap(True)
        # self._song_info_bar.set_padding(10, 10)
        #
        # self._all_buttonbox = ExpandedButtonBox()
        # self._add_all = self._all_buttonbox.add_labeled('Add all')
        # self._rem_all = self._all_buttonbox.add_labeled('Remove all')
        #
        # self._sel_buttonbox = ExpandedButtonBox()
        # self._add_sel = controls.ControlButton('list-add')
        # self._add_sel.set_tooltip_markup('Add selected')
        # self._rem_sel = controls.ControlButton('list-remove')
        # self._rem_sel.set_tooltip_markup('Remove selected')
        # self._sel_buttonbox.add(self._add_sel)
        # self._sel_buttonbox.add(self._rem_sel)
        #
        # self._song_action_bar.add(self._all_buttonbox)
        # self._song_action_bar.add(self._sel_buttonbox)
        # self._songsbox.pack_start(self._song_info_bar, False, False, 0)
        # self._songsbox.pack_end(self._song_action_bar, False, False, 0)
        # self._add_all.connect('clicked', self._on_add_all)
        # self._rem_all.connect('clicked', self._on_rem_all)
        # self._add_sel.connect('clicked', self._on_add_sel)
        # self._rem_sel.connect('clicked', self._on_rem_sel)
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
        if self._selected_album.is_compilation:
            # todo add button to jump to comp album
            pass
        year = GLib.markup_escape_text(str(self._selected_album.date))
        self._song_info_bar.set_markup(
            f'<b><big>{title}</big></b>\n<small>{year}</small>')

    def clear_songs(self):
        # for c in self._songsbox.get_children():
        #     if c != self._song_action_bar and c != self._song_info_bar:
        #         c.destroy()
        pass

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
        # self._song_info_bar.set_markup('')
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


if __name__ == '__main__':
    main_window = Gtk.Window()
    main_window.connect('destroy', Gtk.main_quit)
    main_window.set_title('NeonMeate')

    album_pixbuf = GdkPixbuf.Pixbuf.new_from_file(
        '/media/josh/Music/Neurosis/Through Silver in Blood/cover.jpg')
    scaled_pixbuf = album_pixbuf.scale_simple(160, 160,
                                              GdkPixbuf.InterpType.BILINEAR)
    album_img = Gtk.Image.new_from_pixbuf(scaled_pixbuf)

    toplevel_album_box = Gtk.VBox()
    toplevel_album_box.set_margin_start(160)
    toplevel_album_box.set_margin_end(160)
    toplevel_album_box.set_margin_bottom(48)
    toplevel_album_box.set_margin_top(48)

    album_info_box = Gtk.VBox()
    album_info_box.set_property('can-focus', False)
    album_info_box.set_halign(Gtk.Align.FILL)
    album_info_box.set_hexpand(True)
    album_info_box.set_property('spacing', 32)

    img_box = Gtk.Box()
    img_box.set_property('can-focus', False)
    img_box.set_halign(Gtk.Align.CENTER)
    img_box.set_valign(Gtk.Align.START)
    img_box.set_homogeneous(False)
    img_box.add(album_img)

    album_details = Gtk.VBox()
    album_details.set_property('can-focus', False)
    album_details.set_halign(Gtk.Align.CENTER)
    album_details.set_valign(Gtk.Align.START)
    album_details.set_margin_top(18)
    title_label = Gtk.Label()
    title_label.set_halign(Gtk.Align.START)
    title_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
    title_label.set_margin_bottom(18)
    title_label.set_markup('Through Silver in Blood')
    album_details.add(title_label)
    album_info_box.add(img_box)
    album_info_box.add(album_details)
    toplevel_album_box.add(album_info_box)
    main_window.add(toplevel_album_box)
    main_window.show_all()
    Gtk.main()
