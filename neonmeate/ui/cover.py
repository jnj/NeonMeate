import cairo
import gi
import logging

from gi.repository import GdkPixbuf, Gtk, Gdk, GLib

from neonmeate import cluster
from neonmeate.color import RGBColor
from neonmeate.ui.toolkit import gtk_main

gi.require_version('Gtk', '3.0')
gi.require_foreign('cairo')


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


# noinspection PyUnresolvedReferences
class CoverWithGradient(Gtk.DrawingArea):
    def __init__(self, pixbuf, rng, executor):
        super(CoverWithGradient, self).__init__()
        self._rng = rng
        self.w = 600
        self.h = 600
        self.edge_size = self.w
        self.set_size_request(self.h, self.w)
        self.pixbuf = pixbuf
        self.connect('draw', self.draw)
        self.connect('size-allocate', self.alloc)
        self._grad = Gradient.gray()
        self._border_rgb = 1, 1, 1
        self._is_default_grad = True
        self._border_thickness = 5

        def on_gradient_ready(fut):
            ex = fut.exception(timeout=1)

            if ex is not None:
                logging.exception(ex)
                return
            elif not fut.cancelled():
                clusters = fut.result()

                if len(clusters) > 1:
                    c, b = clusters[0:2]
                    self._update_grad(b.as_rgb(), c.as_rgb())

        cluster_result = executor.submit(cluster.clusterize, pixbuf, self._rng)
        cluster_result.add_done_callback(on_gradient_ready)

    @gtk_main
    def _update_grad(self, rgb, border_rgb):
        if self._is_default_grad:
            self._is_default_grad = False
            start_rgb = rgb
            stop_rgb = start_rgb.darken(18).saturate(5)
            self._grad = Gradient(start_rgb, stop_rgb)
            self._border_rgb = border_rgb.components()
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
        pixbuf_x = (self.w - p.get_width()) / 2
        pixbuf_y = (self.h - p.get_height()) / 2
        Gdk.cairo_set_source_pixbuf(ctx, p, pixbuf_x, pixbuf_y)
        ctx.paint()
        ctx.set_line_width(self._border_thickness)
        r, g, b = self._border_rgb
        ctx.set_source_rgba(r, g, b, 1)
        rect_x = pixbuf_x
        rect_y = pixbuf_y
        rect_width = edge_size
        ctx.rectangle(rect_x, rect_y, rect_width, rect_width)
        ctx.stroke()
        return False
