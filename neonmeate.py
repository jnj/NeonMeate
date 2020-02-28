import logging
import random
import sys

import gi

import neonmeate.artcache as artcache
import neonmeate.mpd.mpdlib as nmpd
import neonmeate.ui.app as app
import neonmeate.nmasync as nmasync

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from concurrent.futures import ThreadPoolExecutor


def main(args):
    music_dir = args[0]
    rng = random.Random()
    rng.seed(39334)
    logging.basicConfig(level=logging.INFO)
    hb_executor = nmasync.ScheduledExecutor()

    with ThreadPoolExecutor(2) as executor:
        mpdclient = nmpd.Mpd(hb_executor, 'localhost', 6600)
        hb = nmpd.MpdHeartbeat(mpdclient, 700, hb_executor)
        mpdclient.connect()
        hb.start()
        art_cache = artcache.ArtCache(music_dir)

        main_window = app.App(rng, mpdclient, executor, art_cache, hb)
        main_window.connect('destroy', Gtk.main_quit)
        main_window.show_all()
        Gtk.main()
        hb_executor.stop()


if __name__ == '__main__':
    main(sys.argv[1:])
