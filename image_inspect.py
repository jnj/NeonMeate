import sys
import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GObject, GLib, GdkPixbuf

import PIL

from PIL import Image


def main(args):
    img = Image.open(args[0])
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(args[0])
    print(f"format={img.format}, size={img.size}, mode={img.mode}, desc={img.format_description}"
          f", bands={img.getbands()}")
    print(f"pixbuf bits-per-sample={pixbuf.props.bits_per_sample}, "
          f"colorspace={pixbuf.props.colorspace}, "
          f"has_alpha={pixbuf.props.has_alpha}, "
          f"n-channels={pixbuf.props.n_channels}, "
          f"rowstride={pixbuf.props.rowstride}, "
          f"rowstride/width={pixbuf.props.rowstride / pixbuf.props.width}, "
          f"width={pixbuf.props.width}"
          )



if __name__ == '__main__':
    main(sys.argv[1:])
