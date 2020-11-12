from gi.repository import GdkPixbuf, GObject, Gtk, Pango, GLib

import functools


def gtk_main(func):
    """
    Wraps a function so that it will run on the main GTK
    thread. Intended for use as a decorator with the
    @ syntax.
    """

    def f(*args):
        GLib.idle_add(func, *args)

    return f


# noinspection PyUnresolvedReferences
class AlbumArt:
    """
    Asynchronously resolved album artwork. This will initially
    be a pixbuf that is the placeholder image, but will change
    to the album artwork once that has been loaded.
    """
    ScaleMode = GdkPixbuf.InterpType.BILINEAR

    def __init__(self, artcache, album, placeholder_pixbuf):
        self._art = artcache
        self._album = album
        self._resolved = None
        self._placeholder = placeholder_pixbuf

    def get_scaled_pixbuf(self, edge_size):
        pixbuf = self._resolved or self._placeholder
        return pixbuf.scale_simple(edge_size, edge_size, AlbumArt.ScaleMode)

    def resolve(self, on_done, user_data):
        """
        Asychronously resolves and loads the cover artwork file into a pixbuf.
        Calls the user-supplied callback with the new pixbuf when done. The
        user_data is arbitrary data that will be passed along to the callback.
        """

        @gtk_main
        def _on_art_ready(pixbuf, data):
            self._resolved = pixbuf
            on_done(pixbuf, data)

        @gtk_main
        def _on_cover_path(cover_path):
            if cover_path:
                self._art.fetch(cover_path, _on_art_ready, user_data)

        self._art.async_resolve_cover_file(self._album.dirpath, _on_cover_path)


# noinspection PyUnresolvedReferences
class Scrollable(Gtk.ScrolledWindow):
    def __init__(self):
        super(Scrollable, self).__init__()
        self._vp = Gtk.Viewport()
        self.add(self._vp)

    def add_content(self, widget):
        self._vp.add(widget)


class CenteredLabel(Gtk.Label):
    def __init__(self, text, markup=False):
        super(CenteredLabel, self).__init__()
        self.set_justify(Gtk.Justification.CENTER)
        self.set_ellipsize(Pango.EllipsizeMode.END)
        self.set_line_wrap(False)
        if markup:
            self.set_markup(text)
        else:
            self.set_text(text)


# noinspection PyUnresolvedReferences,PyArgumentList
class Column(Gtk.ListBox):
    """
    Renders items in a column using a Gtk.ListBox.
    """
    __gsignals__ = {
        'value-selected': (GObject.SignalFlags.RUN_FIRST, None, (str,))
    }

    def __init__(self, vmargin=10, selectable_rows=True):
        super(Column, self).__init__()
        self._vmargin = vmargin
        if selectable_rows:
            self.set_selection_mode(Gtk.SelectionMode.SINGLE)
            super(Column, self).connect('row-selected', self._on_row_selected)
        else:
            self.set_selection_mode(Gtk.SelectionMode.NONE)

    def add_row(self, text):
        label = Gtk.Label(text, xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_margin_top(self._vmargin)
        label.set_margin_bottom(self._vmargin)
        label.show()
        self.add(label)

    # noinspection PyUnusedLocal
    def _on_row_selected(self, box, row):
        child = row.get_child()
        if child and isinstance(child, Gtk.Label):
            self.emit('value-selected', child.get_text())
        return True


# noinspection PyUnresolvedReferences,PyArgumentList
class Table:
    def __init__(self, column_names, column_types):
        self.column_names = column_names
        self.column_types = column_types
        self.model = Gtk.ListStore(*column_types)
        self.tree = None
        self.selection_handler = None

    def clear(self):
        self.model.clear()

    def add(self, col_values):
        self.model.append(col_values)

    def as_widget(self):
        self.tree = Gtk.TreeView.new_with_model(self.model)

        for i, header in enumerate(self.column_names):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(header, renderer, text=i)
            column.set_resizable(True)
            self.tree.append_column(column)

        select = self.tree.get_selection()
        select.connect('changed', self._on_selection_changed)
        self.tree.set_property('fixed_height_mode', True)
        return self.tree

    def _on_selection_changed(self, select):
        model, treeiter = select.get_selected()
        if self.selection_handler:
            if model and model[treeiter]:
                self.selection_handler(model[treeiter])

    def set_selection_handler(self, handler):
        self.selection_handler = handler
