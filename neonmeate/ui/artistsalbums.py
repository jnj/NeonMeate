from gi.repository import GObject, Gtk, GLib, Pango, GdkPixbuf, Gdk

import re

from .controls import ControlButton, NeonMeateButtonBox, PlayModeButton
from neonmeate.ui import toolkit
from neonmeate.ui.toolkit import glib_main, AlbumArt, TimedInfoBar, \
    DiffableBoolean, add_pixbuf_border


class AlbumViewOptions:
    def __init__(self):
        self.num_grid_cols = 1
        self.album_size = 160
        self.col_spacing = 30
        self.row_spacing = 30


# noinspection PyUnresolvedReferences
class ArtistsAlbums(Gtk.Overlay):

    def __init__(self, mpdclient, art, cfg):
        super(ArtistsAlbums, self).__init__()
        album_view_opts = AlbumViewOptions()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._box = Gtk.VBox()
        self.add(self._box)
        self._infobar = TimedInfoBar()
        self._infobar.set_halign(Gtk.Align.START)
        self._infobar.set_valign(Gtk.Align.START)
        self.add_overlay(self._infobar)
        # self.pack_start(self._infobar, False, False, 0)
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

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        columns.pack_start(separator, False, False, 0)

        self._albums_songs = AlbumsAndSongs(
            self._mpdclient,
            self._art,
            self._album_placeholder_pixbuf,
            album_view_opts
        )
        self._albums_songs.connect('playlist-modified', self._on_playlist_mod)
        columns.pack_end(self._albums_songs, True, True, 0)
        self._box.pack_end(columns, True, True, 0)
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


class SongsMenuButtonBox(NeonMeateButtonBox):
    __gsignals__ = {
        'neonmeate_add_sel_click': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_rem_sel_click': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'neonmeate_rep_play_click': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super(SongsMenuButtonBox, self).__init__()
        self._add_sel_btn = ControlButton('list-add-symbolic')
        self.add_button(self._add_sel_btn, 'add-sel', 'neonmeate_add_sel_click')
        self._rem_sel_btn = ControlButton('list-remove-symbolic')
        self.add_button(self._rem_sel_btn, 'rem-sel', 'neonmeate_rem_sel_click')
        self._replace_btn = ControlButton('media-playback-start-symbolic')
        self.add_button(
            self._replace_btn,
            'rep-play',
            'neonmeate_rep_play_click'
        )


# noinspection PyUnresolvedReferences
class SelectSongsButtonBox(NeonMeateButtonBox):
    __gsignals__ = {
        'neonmeate_toggle_selected': (
        GObject.SignalFlags.RUN_FIRST, None, (bool,)),
    }

    def __init__(self):
        super(SelectSongsButtonBox, self).__init__()
        self._toggle_selection_btn = PlayModeButton('object-select-symbolic')
        self.add_button(self._toggle_selection_btn, 'toggle-selection', None)
        self._toggle_selection_btn.set_active(True)
        self._toggle_selection_btn.connect('toggled', self._on_toggled)

    def _on_toggled(self, btn):
        active = btn.get_active()
        self.emit('neonmeate_toggle_selected', active)


# noinspection PyUnresolvedReferences
class SongsMenu(Gtk.Popover):
    __gsignals__ = {
        'playlist-modified': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self, album, mpdclient):
        super(SongsMenu, self).__init__()
        margin = 12
        row_spacing = 10
        self._selected_songs = []
        self._mpdclient = mpdclient
        self._album = album

        self._vbox = Gtk.VBox()
        self.add(self._vbox)
        self._vbox.set_halign(Gtk.Align.START)
        self._songslist = Gtk.VBox()
        self._songslist.set_spacing(row_spacing)
        self._songslist.set_halign(Gtk.Align.START)
        self._songslist.set_margin_top(margin)
        self._songslist.set_margin_bottom(margin)
        self._songslist.set_margin_start(margin)
        self._songslist.set_margin_end(margin)
        self._songs = album.sorted_songs()

        self._scrollable = Gtk.ScrolledWindow()
        self._scrollable.set_propagate_natural_height(True)
        self._scrollable.set_propagate_natural_width(True)
        self._scrollable.set_max_content_width(360)
        self._scrollable.set_max_content_height(400)
        self._scrollable.set_overlay_scrolling(True)
        self._scrollable.set_shadow_type(Gtk.ShadowType.NONE)
        self._scrollable.add(self._songslist)
        multidisc = len(set(song.discnum for song in self._songs)) > 1
        last_discnum = None

        for song in self._songs:
            if multidisc and song.discnum != last_discnum:
                disc_label = Gtk.Label()
                disc_label.set_markup(f'<b>Disc {song.discnum}</b>')
                disc_label.set_xalign(0)
                if last_discnum is not None:
                    disc_label.set_margin_top(12)
                self._songslist.add(disc_label)
            last_discnum = song.discnum
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

        self._all_buttons = Gtk.HBox()
        self._btn_box = SongsMenuButtonBox()
        self._btn_box.set_margin_start(margin)
        self._btn_box.set_margin_top(margin)
        self._btn_box.set_margin_bottom(margin)
        self._btn_box.set_margin_end(margin)
        self._btn_box.set_halign(Gtk.Align.START)
        self._btn_box.connect('neonmeate_add_sel_click', self._on_add_sel)
        self._btn_box.connect('neonmeate_rem_sel_click', self._on_rem_sel)
        self._btn_box.connect('neonmeate_rep_play_click', self._on_replace)
        self._all_buttons.pack_start(self._btn_box, False, False, 0)
        self._toggle_selection_btn = SelectSongsButtonBox()
        self._toggle_selection_btn.set_margin_start(margin)
        self._toggle_selection_btn.set_margin_top(margin)
        self._toggle_selection_btn.set_margin_bottom(margin)
        self._toggle_selection_btn.set_margin_end(margin)
        self._toggle_selection_btn.set_halign(Gtk.Align.END)
        self._toggle_selection_btn.connect(
            'neonmeate_toggle_selected',
            self._on_selection_toggled
        )
        self._all_buttons.pack_end(self._toggle_selection_btn, False, False, 0)
        self._vbox.pack_start(self._all_buttons, False, False, 0)
        self._vbox.pack_end(self._scrollable, True, True, 10)
        self._vbox.show_all()

    def _on_selection_toggled(self, btnbox, active):
        for child in self._songslist.get_children():
            if isinstance(child, Gtk.CheckButton):
                if child.get_active() != active:
                    child.set_active(active)

    def _get_selected_songs(self):
        return self._selected_songs

    def _on_replace(self, _):
        self._mpdclient.clear_playlist()
        self._add_selected()
        self._mpdclient.toggle_pause(0)

    def _on_add_sel(self, btn):
        self._add_selected()

    def _add_selected(self):
        songs = self._get_selected_songs()
        if songs:
            self._mpdclient.add_songs(songs)
            self.emit('playlist-modified')

    def _on_rem_sel(self, btn):
        songs = self._get_selected_songs()
        if songs:
            self._mpdclient.remove_songs(songs)
            self.emit('playlist-modified')


# noinspection PyUnresolvedReferences
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

    # def do_get_preferred_width(self):
    #     w = 240
    #     return w, w

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
        'playlist-modified': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    @staticmethod
    def album_sort_key(album):
        return album.date, album.title, album.artist

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf, options):
        super(Albums, self).__init__()
        self.set_shadow_type(Gtk.ShadowType.NONE)
        self._placeholder_pixbuf = placeholder_pixbuf
        self._album_width_px = options.album_size
        self._album_spacing = options.col_spacing
        self.set_min_content_width(self._album_width_px + self._album_spacing)
        self._art = art_cache
        self._mpdclient = mpdclient
        self._options = options
        self._model = Gtk.ListStore(GObject.TYPE_PYOBJECT)
        self._view = Gtk.IconView(self._model)
        self._view.set_hexpand(True)
        self._view.set_selection_mode(Gtk.SelectionMode.NONE)
        self._view.set_column_spacing(options.col_spacing)
        self._view.set_row_spacing(options.row_spacing)
        self._view.set_has_tooltip(True)
        self._view.set_item_width(self._album_width_px)
        self._view.connect('query-tooltip', self._on_tooltip)
        self.add(self._view)
        self._surface_cache = {}

        renderer = Gtk.CellRendererPixbuf()
        self._view.pack_start(renderer, False)
        context = self.get_style_context()
        border_color = context.get_color(context.get_state())
        self._placeholder_surface = self.pixbuf_surface(
            add_pixbuf_border(self._placeholder_pixbuf, border_color))

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
                context = self.get_style_context()
                border_color = context.get_color(context.get_state())
                surface = self.pixbuf_surface(
                    add_pixbuf_border(pb, border_color))
                self._surface_cache[album] = surface
            cell.set_property('surface', surface)

        self._view.set_cell_data_func(renderer, render_cover, None)

        def render_album_info(view, cell, model, iter, data):
            album = model[iter][0]
            esc_title = GLib.markup_escape_text(album.title)
            esc_date = GLib.markup_escape_text(str(album.date))
            markup = f'{esc_title}\n<small>{esc_date}</small>'
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

    def _on_playlist_modified(self, _):
        self.emit('playlist-modified')

    def _on_right_click(self, widget, event):
        path, path_iter = self._get_path_at_position(event, widget)
        if path:  # event.button == Gdk.BUTTON_PRIMARY and path:
            popover = SongsMenu(self._model[path_iter][0], self._mpdclient)
            popover.connect('playlist-modified', self._on_playlist_modified)
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
        self._albums = Albums(
            self._mpdclient,
            self._art_cache,
            placeholder_pixbuf,
            albums_view_options)
        self._albums.connect('album-selected', self._on_album_selected)
        self._albums.connect('playlist-modified', self._on_playlist_modified)
        self.add(self._albums)
        self._albums_list = []
        self._artist_by_name = {}
        self._selected_artist = None
        self._selected_album = None
        self._current_songs = None
        self.show_all()

    def _on_album_selected(self, albums, index):
        album = albums.get_selected_album()
        self._selected_album = album
        self._update_song_info()
        self.clear_songs()
        self._current_songs = Songs(album)
        self._current_songs.show()
        self._songsbox.pack_end(self._current_songs, True, True, 0)
        self.queue_draw()

    def clear(self):
        self._albums.clear()
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
        artist_inst = self._artist_by_name[artist_name]

        @glib_main
        def on_albums(albums):
            self._albums_list.clear()
            self._albums_list.extend(albums)
            self._selected_artist = artist_name
            self._albums.on_artist_selected(artist_name, albums)

        self._mpdclient.find_albums(artist_inst, on_albums)

    def _on_playlist_modified(self, _):
        self.emit('playlist-modified')


# noinspection PyArgumentList,PyUnresolvedReferences
class ArtistsContainer(Gtk.VBox):
    __gsignals__ = {
        'artist_selected': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'artists_loaded': (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self, mpdclient):
        super(ArtistsContainer, self).__init__()
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
