import cairo
import gi
import logging

from gi.repository import GdkPixbuf, Gtk, Gdk

from neonmeate.util import cluster
from neonmeate.util.color import RGBColor
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
    ScaleMode = GdkPixbuf.InterpType.BILINEAR

    @staticmethod
    def rand_switch(rng, a, b):
        if rng.randint(1, 100) >= 50:
            return a, b
        else:
            return b, a

    def __init__(self, pixbuf, rng, executor, cfg, artist, album):
        super(CoverWithGradient, self).__init__()
        self.logger = logging.getLogger(__name__)
        self._rng = rng
        self._cfg = cfg
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
        self.artist = artist
        self.album = album

        def on_gradient_ready(fut):
            ex = fut.exception(timeout=1)

            if ex is not None:
                self.logger.exception(ex)
                return
            elif not fut.cancelled():
                clusterer, _, clusters, _ = fut.result()
                if len(clusters) < 2:
                    return
                result = cluster.ClusteringResult(
                    clusters,
                    clusterer._colorspace
                )

                bordercolor, start = result.complementary(), result.dominant()
                self._update_grad(start, bordercolor)
                self._cfg.save_clusters(self.artist, self.album, clusters)

        border, bg = self._cfg.get_background(artist, album, rng)

        if border is not None and bg is not None:
            a, b = CoverWithGradient.rand_switch(self._rng, border, bg)
            self._update_grad(RGBColor(*a), RGBColor(*b))
        else:
            cluster_result = executor.execute_async(
                cluster.clusterize,
                pixbuf,
                self._rng,
                200,
                7,
                0.001,
                200,
                'rgb')
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
        p = self._scale(edge_size)
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

    def _scale(self, size):
        return self.pixbuf.scale_simple(size, size, CoverWithGradient.ScaleMode)
