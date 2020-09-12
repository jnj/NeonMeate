import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from concurrent.futures import ThreadPoolExecutor

import logging
import logging.config
import random
import sys
import time

import neonmeate.mpd.mpdlib as nmpd
import neonmeate.ui.app as app
import neonmeate.util.art as artcache
import neonmeate.util.config as config
import neonmeate.util.thread as thread


def configure_logging():
    logging.config.dictConfig({
        'version': 1,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'default',
                'stream': 'ext://sys.stdout'
            }
        },
        'formatters': {
            'default': {
                'format': '%(asctime)s %(levelname)s [%(name)s] - %(message)s'
            }
        },
        'loggers': {
            'neonmeate': {
                'handlers': ['console'],
                'level': 'INFO'
            }
        }
    })


# noinspection PyUnresolvedReferences
def main(args):
    configure_logging()
    cfg = config.Config.load_main_config()
    music_dir = cfg['media_dir']
    rng = random.Random()
    rng.seed(int(1000 * time.time()))
    hb_executor = thread.ScheduledExecutor()

    with ThreadPoolExecutor(2) as executor:
        mpdclient = nmpd.Mpd(hb_executor, cfg.mpd_host(), cfg.mpd_port())
        hb = nmpd.MpdHeartbeat(mpdclient, 700, hb_executor)
        mpdclient.connect()
        hb.start()
        art_cache = artcache.ArtCache(music_dir, executor)

        main_window = app.App(rng, mpdclient, executor, art_cache, hb, cfg)
        main_window.connect('destroy', Gtk.main_quit)
        main_window.show_all()
        Gtk.main()
        cfg.save(config.main_config_file())
        logging.shutdown()
        hb_executor.stop()


if __name__ == '__main__':
    main(sys.argv[1:])
