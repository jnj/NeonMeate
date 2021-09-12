from gi.repository import Gtk, GObject, GLib, Pango, Gdk

from neonmeate.ui.songs_menu_widget import SongsMenu
from neonmeate.ui.toolkit import add_pixbuf_border, AlbumArt


class Albums(Gtk.ScrolledWindow):
    __gsignals__ = {
        'album-selected': (GObject.SignalFlags.RUN_FIRST, None, (int,)),
    }

    @staticmethod
    def album_sort_key(album):
        return album.date, album.title, album.artist

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf, options,
                 border_style_context):
        super(Albums, self).__init__()
        self.set_shadow_type(Gtk.ShadowType.NONE)
        self._border_style_context = border_style_context
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
        self._border_color = border_style_context.get_background_color(0)
        self._placeholder_surface = self.pixbuf_surface(
            add_pixbuf_border(self._placeholder_pixbuf, self._border_color,
                              border_width=0))

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
                pb = add_pixbuf_border(
                    album.art.get_scaled_pixbuf(self._album_width_px),
                    self._get_border_color(),
                    border_width=self._options.border_width
                )
                surface = self.pixbuf_surface(pb)
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
        self._view.connect('button-press-event', self._on_button_press)
        self._selected_artist = None
        self._selected_album = None
        self._artists = []
        self.show_all()

    def on_theme_change(self):
        self._surface_cache.clear()

    def _get_border_color(self):
        flags = Gtk.StateFlags.NORMAL
        return self._border_style_context.get_background_color(flags)

    def _on_button_press(self, widget, event):
        path, path_iter = self._get_path_at_position(event, widget)
        if path:  # event.button == Gdk.BUTTON_PRIMARY and path:
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
        self._surface_cache.clear()

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
        self._surface_cache.clear()
        self._selected_artist = artist_name
        for album in sorted(list(albums), key=Albums.album_sort_key):
            self._model.append([album])