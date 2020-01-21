import gi

gi.require_version('Gtk', '3.0')

from gi.repository import GdkPixbuf, Gtk, Gdk, GLib
import cairo


def pixbuf_from_file(fileobj):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(fileobj.name)
    return pixbuf


class App(Gtk.ApplicationWindow):
    def __init__(self):
        Gtk.Window.__init__(self, title="Cover")
        self.set_default_size(600, 600)
        self._titlebar = Gtk.HeaderBar()
        self._titlebar.set_title("Cover")
        self._titlebar.set_show_close_button(True)
        self.set_titlebar(self._titlebar)


class CoverImage(Gtk.Grid):
    def __init__(self, pixbuf):
        super(CoverImage, self).__init__()
        pixbuf = pixbuf.scale_simple(200, 200, GdkPixbuf.InterpType.BILINEAR)
        img = Gtk.Image.new_from_pixbuf(pixbuf)
        img.show()
        self.attach(img, 0, 0, 1, 1)


coverpath='/media/josh/Music/Autopsy/Mental Funeral/cover.jpg'

with open(coverpath, 'br') as f:
    p = pixbuf_from_file(f)

main_window = App()
main_window.add(CoverImage(p))
main_window.connect('destroy', Gtk.main_quit)
main_window.show_all()

Gtk.main()

print('done')
