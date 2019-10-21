from gi.repository import Gtk, Pango


class Column(Gtk.ListBox):
    """
    Renders text items in a column using a Gtk.ListBox.
    """
    def __init__(self):
        super(Column, self).__init__()

    def add_row(self, text):
        label = Gtk.Label(text, xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        self.add(label)


class Table:
    def __init__(self, column_names, column_types):
        self.column_names = column_names
        self.column_types = column_types
        self.model = Gtk.ListStore(*column_types)
        self.tree = None
        self.selection_handler = None

    def add(self, col_values):
        self.model.append(col_values)

    def as_widget(self):
        self.tree = Gtk.TreeView.new_with_model(self.model)

        for i, col_header in enumerate(self.column_names):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_header, renderer, text=i)
            column.set_sort_column_id(i)
            column.set_resizable(True)

            self.tree.append_column(column)

        select = self.tree.get_selection()
        select.connect('changed', self._on_selection_changed)
        return self.tree

    def _on_selection_changed(self, select):
        model, treeiter = select.get_selected()
        if self.selection_handler:
            self.selection_handler(model[treeiter])

    def set_selection_handler(self, handler):
        self.selection_handler = handler


if __name__ == "__main__":
    t = Table(['foo', 'bar'], [str, str])

    t.add(['1', '2'])
    t.add(['3', '4'])
    t.add(['5', '6'])

    win = Gtk.Window()
    win.connect('destroy', Gtk.main_quit)
    win.add(t.as_widget())


    def on_select(row):
        print(f"You selected {row[0]} {row[1]}")


    t.set_selection_handler(on_select)
    win.show_all()
    Gtk.main()
