import gi
import cairo
from gi.repository import Gdk, GdkPixbuf


def cairo_surface_create_from_pixbuf(pb, scale_factor, window):
    fmt = cairo.FORMAT_RGB24
    w = pb.get_width()
    h = pb.get_height()
    surf = cairo.ImageSurface(fmt, w, h)
    cr = cairo.Context(surf)
    Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
    cr.paint()
    return surf

