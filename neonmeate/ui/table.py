import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Table:
    def __init__(self, column_names, column_types):
        self.column_names = column_names
        self.column_types = column_types
        self.model = Gtk.ListStore(*column_types)

    def add(self, col_values):
        self.model.append(col_values)

    def as_widget(self):
        tree = Gtk.TreeView.new_with_model(self.model)
        for i, col_header in enumerate(self.column_names):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_header, renderer, text=i)
            tree.append_column(column)
        return tree


if __name__ == "__main__":
    t = Table(['foo', 'bar'], [str, str])

    t.add(['1', '2'])
    t.add(['3', '4'])
    t.add(['5', '6'])

    win = Gtk.Window()
    win.connect('destroy', Gtk.main_quit)
    win.add(t.as_widget())
    win.show_all()
    Gtk.main()
