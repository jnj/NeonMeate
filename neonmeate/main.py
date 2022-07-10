import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, GObject, GLib, Adw

import argparse
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


def configure_logging(debug_enabled):
    level = 'WARN'
    if debug_enabled:
        level = 'DEBUG'
    logging.config.dictConfig({
        'version': 1,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': level,
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
                'level': level
            }
        }
    })


def log_errors(ex):
    logging.exception('Exception caught')


def parseargs(args):
    fmtclass = argparse.ArgumentDefaultsHelpFormatter
    p = argparse.ArgumentParser('neonmeate', formatter_class=fmtclass)
    p.add_argument('-d', '--debug', help='enabled debug output',
                   action='store_const', default=False, const=True)
    return p.parse_args(args)


class NeonMeate(Adw.Application):
    def __init__(self, options, *args, **kwargs):
        super(NeonMeate, self).__init__(application_id='com.github.neonmeate')
        self._options = options
        self.connect('activate', self._on_activate)

    def _on_activate(self, instance):
        @toolkit.glib_main
        def connect(mainwindow):
            mainwindow.on_connect_attempt(
                None,
                cfg.mpd_host(),
                cfg.mpd_port(),
                True
            )

        configure_logging(self._options.debug)
        cfg = config.Config.load_main_config()
        configstate = config.ConfigState()
        configstate.init_from_cfg(cfg)
        rng = random.Random()
        rng.seed(int(1000 * time.time()))

        self._executor = exec = thread.ScheduledExecutor(log_errors, log_errors)
        self._executor.start()

        self._connstatus = nmpd.MpdConnectionStatus()
        self._mpdclient = nmpd.Mpd(exec, configstate, self._connstatus)
        hb_interval = cfg.mpd_hb_interval()
        self._hb = nmpd.MpdHeartbeat(self._mpdclient, hb_interval, exec, self._connstatus)
        self._art_cache = artcache.ArtCache(configstate, exec)

        main_window = app.App(
            instance,
            rng,
            self._mpdclient,
            exec,
            self._art_cache,
            self._hb,
            cfg,
            configstate,
            self._connstatus
        )

        # main_window.connect('destroy', Gtk.main_quit)
        main_window.set_title('NeonMeate')
        # main_window.show_all()
        connect(main_window)
        main_window.present()

        # Gtk.main()
        # hb.stop()
        # cfg.set_connected(connstatus.is_connected())
        # cfg.save(config.main_config_file())
        # logging.shutdown()


# noinspection PyUnresolvedReferences
def main(args=None):
    if not args:
        args = sys.argv[1:]
    options = parseargs(args)
    application = NeonMeate(options)
    application.run(None)


if __name__ == '__main__':
    main(sys.argv[1:])
