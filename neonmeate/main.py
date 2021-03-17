import gi

gi.require_version('Gtk', '3.0')

from gi.repository import Gtk, GObject, GLib

import logging
import logging.config
import random
import sys
import time

import neonmeate.nmpd.mpdlib as nmpd
import neonmeate.ui.app as app
import neonmeate.ui.toolkit as toolkit
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
                'level': 'DEBUG'
            }
        }
    })


def log_errors(ex):
    logging.exception('Exception caught')


# noinspection PyUnresolvedReferences
def main(args=None):
    if not args:
        args = sys.argv[1:]

    configure_logging()
    cfg = config.Config.load_main_config()
    configstate = config.ConfigState()
    configstate.init_from_cfg(cfg)
    rng = random.Random()
    rng.seed(int(1000 * time.time()))

    with thread.ScheduledExecutor(log_errors, log_errors) as executor:
        connstatus = nmpd.MpdConnectionStatus()
        mpdclient = nmpd.Mpd(executor, configstate, connstatus)
        hb_interval = cfg.mpd_hb_interval()
        hb = nmpd.MpdHeartbeat(mpdclient, hb_interval, executor, connstatus)
        art_cache = artcache.ArtCache(configstate, executor)

        main_window = app.App(
            rng,
            mpdclient,
            executor,
            art_cache,
            hb,
            cfg,
            configstate,
            connstatus
        )

        main_window.connect('destroy', Gtk.main_quit)
        main_window.set_title('NeonMeate')
        main_window.show_all()

        @toolkit.glib_main
        def connect():
            if cfg.is_connected():
                main_window.on_connect_attempt(
                    None,
                    cfg.mpd_host(),
                    cfg.mpd_port(),
                    True
                )

        connect()
        Gtk.main()
        hb.stop()
        cfg.set_connected(connstatus.is_connected())
        cfg.save(config.main_config_file())
        logging.shutdown()


if __name__ == '__main__':
    main(sys.argv[1:])
