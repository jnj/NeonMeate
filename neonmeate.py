import logging
import random
import sys

import gi

import neonmeate.artcache as artcache
import neonmeate.mpd.cache as nmcache
import neonmeate.mpd.mpdlib as nmpd
import neonmeate.ui.app as app

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from concurrent.futures import ThreadPoolExecutor


def main(args):
    music_dir = args[0]
    rng = random.Random()
    rng.seed(39334)
    logging.basicConfig(level=logging.INFO)

    with ThreadPoolExecutor(2) as executor:
        mpdclient = nmpd.Mpd(executor, 'localhost', 6600)
        mpdclient.connect()

        album_cache = nmcache.AlbumCache(music_dir)
        mpdclient.populate_cache(album_cache)

        art_cache = artcache.ArtCache()
        main_window = app.App(rng, mpdclient, executor, album_cache, art_cache)
        main_window.connect('destroy', Gtk.main_quit)
        main_window.show_all()
        Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1:])
