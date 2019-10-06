import os
import sys
import math
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf


class MyWindow(Gtk.Window):
    def __init__(self, covers):
        Gtk.Window.__init__(self, title="PyMusic")
        self.set_default_size(4 * 200 + 3 * 5, 4 * 200 + 3 * 5)
        self.covers = covers
        self.grid = Gtk.Grid()
        self.grid.set_row_homogeneous(True)
        self.grid.set_column_homogeneous(True)
        self.grid.set_column_spacing(5)
        self.grid.set_row_spacing(5)

        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.add(self.grid)
        self.add(self.scrolled)

        attach_row = 0
        attach_col = 0
        count = 0
        width = 10

        for cover in self.covers:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(cover)
            pixbuf = pixbuf.scale_simple(200, 200, GdkPixbuf.InterpType.BILINEAR)
            img = Gtk.Image.new_from_pixbuf(pixbuf)

            if count == width:
                attach_row += 1
                attach_col = 0
                count = 0

            self.grid.attach(img, attach_col, attach_row, 1, 1)
            attach_col += 1
            count += 1


def each_cover(path):
    if os.path.isfile(path) and path[-9:] == 'cover.jpg':
        yield path
    elif os.path.isdir(path):
        children = os.listdir(path)
        for c in children:
            for f in each_cover(os.path.join(path, c)):
                yield f


def main(args):
    i = 0
    covers = []
    for cover in each_cover('/media/josh/Music'):
        covers.append(cover)
        i += 1
        if i == 200:
            break
    print(covers)
    win = MyWindow(covers)
    win.connect('destroy', Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1:])
