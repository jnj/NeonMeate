import gi

gi.require_version('Gtk', '3.0')
gi.require_foreign('cairo')

from gi.repository import GdkPixbuf, Gtk, Gdk, GLib
import cairo
from neonmeate import cluster


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
        self.w = 600
        self.h = 600
        self.set_size_request(self.h, self.w)
        self.pixbuf = pixbuf
        self.connect('draw', self.draw)
        self.connect('size-allocate', self.alloc)
        self.clusters = cluster.clusterize(pixbuf)
        self.start = self.clusters[-1].mean

    def alloc(self, widget, allocation):
        self.h = allocation.height
        self.w = allocation.width

    def draw(self, da, ctx):
        grad = cairo.LinearGradient(0, 0, 0, self.h)
        # red-to-black linear gradient
        l = [x / 255 for x in self.start]
        m = [x * 0.6 for x in l]
        grad.add_color_stop_rgb(0, l[0], l[1], l[2])
        grad.add_color_stop_rgb(1, m[0], m[1], m[2])
        ctx.set_source(grad)
        ctx.rectangle(0, 0, self.w, self.h)
        ctx.fill()
        p = self.pixbuf.scale_simple(self.w - 200, self.h - 200, GdkPixbuf.InterpType.BILINEAR)
        Gdk.cairo_set_source_pixbuf(ctx, p, (self.w - p.get_width()) / 2, (self.h - p.get_height()) / 2)
        ctx.paint()
        return False


coverpath = '/media/josh/Music/Death/Individual Thought Patterns/cover.jpg'

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
