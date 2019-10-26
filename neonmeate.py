import os
import sys

import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk

import neonmeate.mpd.cache as nmcache
import neonmeate.mpd.mpdlib as nmpd
import neonmeate.ui.app as app


def each_cover(path):
    if os.path.isfile(path) and path[-9:] == 'cover.jpg':
        yield path
    elif os.path.isdir(path):
        children = os.listdir(path)
        for c in children:
            for f in each_cover(os.path.join(path, c)):
                yield f


# stack switcher example
class Example(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="NeonMeate")
        self.stack = Gtk.Stack()
        self.headerbar = Gtk.HeaderBar()
        self.set_titlebar(self.headerbar)
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        self.add(self.stack)

        checkbutton = Gtk.CheckButton("Click me!")
        self.stack.add_titled(checkbutton, "check", "Check Button")

        label = Gtk.Label()
        label.set_markup("<big>A fancy label</big>")
        self.stack.add_titled(label, "label", "A label")

        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self.stack)
        self.headerbar.pack_start(stack_switcher)


def main(args):
    num_covers = 1

    i = 0
    covers = []
    for cover in each_cover('/media/josh/Music'):
        covers.append(cover)
        i += 1
        if i == num_covers:
            break

    mpdclient = nmpd.Mpd('localhost', 6600)
    mpdclient.connect()

    album_cache = nmcache.AlbumCache()
    mpdclient.populate_cache(album_cache)

    main_window = app.App(mpdclient, covers, album_cache)
    main_window.connect('destroy', Gtk.main_quit)
    main_window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1:])
