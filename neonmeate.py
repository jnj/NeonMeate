import sys

import gi

import neonmeate.mpd.cache as nmcache
import neonmeate.mpd.mpdlib as nmpd
import neonmeate.artcache as artcache
import neonmeate.ui.app as app

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk


def main(args):
    mpdclient = nmpd.Mpd('localhost', 6600)
    mpdclient.connect()

    album_cache = nmcache.AlbumCache('/media/josh/Music')
    mpdclient.populate_cache(album_cache)

    art_cache = artcache.ArtCache()
    main_window = app.App(mpdclient, [], album_cache, art_cache)
    main_window.connect('destroy', Gtk.main_quit)
    main_window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1:])
