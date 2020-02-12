import cairo
import gi
from gi.repository import GdkPixbuf, Gtk, Gdk, GLib

from neonmeate import cluster
from neonmeate.color import RGBColor

gi.require_version('Gtk', '3.0')
gi.require_foreign('cairo')


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


class Gradient:
    """
    Linear gradient descriptor. Start and stop are RGBColor instances.
    """

    @staticmethod
    def gray():
        start = RGBColor(*([0.2] * 3))
        stop = start.darken(15)
        return Gradient(start, stop)

    def __init__(self, start, stop):
        self.start = start
        self.stop = stop

    def __str__(self):
        return str(self.start)


class CoverWithGradient(Gtk.DrawingArea):
    def __init__(self, pixbuf, executor):
        super(CoverWithGradient, self).__init__()
        self.w = 600
        self.h = 600
        self.edge_size = self.w
        self.set_size_request(self.h, self.w)
        self.pixbuf = pixbuf
        self.connect('draw', self.draw)
        self.connect('size-allocate', self.alloc)
        self._grad = Gradient.gray()
        self._is_default_grad = True

        def on_gradient_ready(fut):
            if not fut.cancelled() and fut.exception(timeout=1) is None:
                clusters = fut.result()
                #newline = '\n'
                #print(f"clusters: {newline.join([str(c) for c in clusters])}")
                if len(clusters) > 0:
                    c = clusters[0]
                    GLib.idle_add(self._update_grad, c.mean_as_rgbcolor())

        cluster_result = executor.submit(cluster.clusterize, pixbuf)
        cluster_result.add_done_callback(on_gradient_ready)

    def _update_grad(self, rgb):
        if self._is_default_grad:
            self._is_default_grad = False
            start_rgb = rgb
            stop_rgb = start_rgb.darken(18).saturate(5)
            self._grad = Gradient(start_rgb, stop_rgb)
            self.queue_draw()

    def alloc(self, widget, allocation):
        self.h = allocation.height
        self.w = allocation.width
        self.edge_size = min(self.w, self.h)

    def draw(self, draw_area_obj, ctx):
        grad = cairo.LinearGradient(0, 0, 0, self.h)
        grad.add_color_stop_rgb(0, *self._grad.start.rgb)
        grad.add_color_stop_rgb(1, *self._grad.stop.rgb)

        ctx.set_source(grad)
        ctx.rectangle(0, 0, self.w, self.h)
        ctx.fill()
        edge_size = self.edge_size - 200
        p = self.pixbuf.scale_simple(edge_size, edge_size, GdkPixbuf.InterpType.BILINEAR)
        Gdk.cairo_set_source_pixbuf(ctx, p, (self.w - p.get_width()) / 2, (self.h - p.get_height()) / 2)
        ctx.paint()
        return False
