import sys

import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class Handler:
    def on_destroy(self, *args):
        Gtk.main_quit()

    def onButtonPressed(self, button):
        pass


def main(args):
    builder = Gtk.Builder()
    builder.add_from_file("neonmeate.glade")
    builder.connect_signals(Handler())
    window = builder.get_object('MainWindow')
    window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1:])
