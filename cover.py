import gi

gi.require_version('Gtk', '3.0')
gi.require_foreign('cairo')

from gi.repository import GdkPixbuf, Gtk, Gdk, GLib
import cairo


def pixbuf_from_file(fileobj):
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(fileobj.name)
    return pixbuf


def scale_pixbuf(pixbuf, window):
    return pixbuf.scale_simple(window.get_width(), window.get_height(), GdkPixbuf.InterpType.BILINEAR)


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
        pixbuf = pixbuf.scale_simple(400, 400, GdkPixbuf.InterpType.BILINEAR)
        img = Gtk.Image.new_from_pixbuf(pixbuf)
        img.show()
        self.attach(img, 0, 0, 1, 1)


class CoverWithGradient(Gtk.DrawingArea):
    def __init__(self, pixbuf):
        super(CoverWithGradient, self).__init__()
        self.set_size_request(600, 600)
        self.pixbuf = pixbuf
        self.connect('draw', self.draw)

    def draw(self, da, ctx):
        # grad = cairo.LinearGradient(0, 0, 0, 400)
        grad = cairo.LinearGradient(0, 0, 0, 600)
        # red-to-black linear gradient
        grad.add_color_stop_rgba(0, 0.2, 0.01, 0.01, 1)
        grad.add_color_stop_rgba(1, 0.3, 0.2, 0.2, 1)
        ctx.set_source(grad)
        # ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.rectangle(0, 0, 600, 600)
        ctx.fill()
        Gdk.cairo_set_source_pixbuf(ctx, self.pixbuf, 100, 100)
        ctx.paint()
        print('draw complete!')
        return False


coverpath = '/media/josh/Music/Autopsy/Mental Funeral/cover.jpg'

with open(coverpath, 'br') as f:
    p = pixbuf_from_file(f)

main_window = App()
# main_window.add(CoverImage(p))
drawing_area = CoverWithGradient(p)
main_window.add(drawing_area)

main_window.connect('destroy', Gtk.main_quit)
main_window.show_all()

Gtk.main()

print('done')
