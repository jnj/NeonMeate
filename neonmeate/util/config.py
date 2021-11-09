import hashlib
import json
import os

from gi.repository import GObject


class ConfigKey:
    MEDIA_DIR = 'media_dir'
    CONN_SETTINGS = 'nmpd'
    CONN_HOST = 'host'
    CONN_PORT = 'port'
    CONN_HB = 'hb'
    CONNECTED = 'connected'
    ALBUM_SIZE = 'album_size'


def main_config_file():
    return os.path.join(neonmeate_config_dir(), 'neonmeate.json')


def neonmeate_config_dir():
    return os.path.join(user_config_dir(), 'neonmeate')


def user_config_dir():
    config_home = os.getenv('XDG_CONFIG_HOME')

    if config_home:
        return os.path.abspath(config_home)

    return os.path.join(user_home(), ".config")


def user_home():
    return os.path.expanduser("~")


class Config:
    Defaults = {
        # Where to find album art
        ConfigKey.MEDIA_DIR: os.path.join(user_home(), 'Music'),

        # Whether to persist the computed color gradient backgrounds
        # in configuration so that they can be loaded later (this will
        # load them quickly whereas computing the clusters for the
        # gradient can take a little while).
        'cache_backgrounds': True,

        ConfigKey.CONNECTED: False,

        'background_cache': {},

        # Whether to include compilation appearances among an
        # artist's albums in the library view
        'albums_include_comps': True,

        ConfigKey.ALBUM_SIZE: 120,

        ConfigKey.CONN_SETTINGS: {
            ConfigKey.CONN_HOST: 'localhost',
            ConfigKey.CONN_PORT: 6600,
            ConfigKey.CONN_HB: 500
        }
    }

    @staticmethod
    def load_main_config():
        file = main_config_file()
        if os.path.exists(file):
            return Config.load_from(file)
        return Config({})

    @staticmethod
    def load_from(file):
        with open(file, 'r') as f:
            return Config(json.load(f))

    @staticmethod
    def hash_file(filepath):
        m = hashlib.sha1()
        with open(filepath, 'rb') as f:
            m.update(f.read())
        return m.hexdigest()

    def __init__(self, dictlike):
        self._config = dictlike
        self._merge_with_defaults()

    def __getitem__(self, item):
        if item in self._config:
            return self._config[item]
        return Config.Defaults[item]

    def __contains__(self, item):
        return item in self._config

    def _merge_with_defaults(self):
        self._merge(Config.Defaults, self._config)

    def _merge(self, defaults, target):
        if isinstance(defaults, dict):
            for k, v in defaults.items():
                if k in target:
                    self._merge(v, target[k])
                else:
                    target[k] = v

    def set(self, key, item):
        self._config[key] = item

    def save_default(self):
        self.save(main_config_file())

    def save(self, file):
        if not os.path.exists(os.path.dirname(file)):
            os.makedirs(os.path.dirname(file))
        with open(file, 'w') as f:
            json.dump(self._config, f)

    def mpd_hb_interval(self):
        return self._config.get(ConfigKey.CONN_HB, 500)

    def album_size(self):
        return self[ConfigKey.ALBUM_SIZE]

    def save_album_size(self, size):
        self.set(ConfigKey.ALBUM_SIZE, size)
        self.save_default()

    def mpd_host(self):
        return self[ConfigKey.CONN_SETTINGS][ConfigKey.CONN_HOST]

    def mpd_port(self):
        return self[ConfigKey.CONN_SETTINGS][ConfigKey.CONN_PORT]

    def set_connected(self, connected):
        self._config[ConfigKey.CONNECTED] = connected

    def is_connected(self):
        return self[ConfigKey.CONNECTED]

    def set_music_dir(self, value):
        self._config[ConfigKey.MEDIA_DIR] = value

    def set_albums_include_comps(self, enabled):
        self._config['albums_include_comps'] = enabled

    def get_albums_include_comps(self):
        return self._config['albums_include_comps']

    def clear_background_cache(self):
        self._config['background_cache'] = {}

    def get_background(self, artist, album, covpath, rng):
        cache = self['background_cache']
        covdict = cache.get(covpath, None)
        if covdict is not None:
            saved_hash = covdict.get('hash', None)
            calc_hash = Config.hash_file(covpath)
            if saved_hash and calc_hash == saved_hash:
                clusters = covdict['clusters']
                if clusters:
                    fore = rng.choice(clusters)
                    back = rng.choice(clusters)
                    while fore == back:
                        back = rng.choice(clusters)
                    return fore, back
        return None, None

    def save_clusters(self, artist, album, clusters, covpath):
        cache = self['background_cache']
        cover_hash = Config.hash_file(covpath)
        d = {'hash': cover_hash, 'clusters': [c.centroid() for c in clusters]}
        cache[covpath] = d


# noinspection PyUnresolvedReferences
class ConfigState(GObject.GObject):
    """
    This holds the player's configuration values, like
    where the user's music is located, and the MPD
    server connection info.
    """
    connected = GObject.Property(type=bool, default=False)
    musicpath = GObject.Property(type=str, default='')
    host_and_port = GObject.Property(type=object, default=None)
    albums_include_comps = GObject.Property(type=bool, default=True)

    def __init__(self):
        GObject.GObject.__init__(self)
        pass

    def init_from_cfg(self, cfg):
        with self.freeze_notify():
            self.set_property('musicpath', cfg[ConfigKey.MEDIA_DIR])
            conn = cfg[ConfigKey.CONN_SETTINGS]
            hostport = [conn[ConfigKey.CONN_HOST], conn[ConfigKey.CONN_PORT]]
            self.set_property('host_and_port', hostport)
            self.set_property(
                'albums_include_comps',
                cfg['albums_include_comps']
            )

    def set_connected(self, value):
        self._update_if_changed('connected', value)

    def get_connected(self):
        return self.get_property('connected')

    def set_albums_include_comps(self, enabled):
        self._update_if_changed('albums_include_comps', enabled)

    def set_musicpath(self, path):
        self._update_if_changed('musicpath', path)

    def get_musicpath(self):
        return self.get_property('musicpath')

    def get_host_and_port(self):
        return self.get_property('host_and_port')

    def set_host_and_port(self, host, port):
        self._update_if_changed('host_and_port', [host, port])

    # todo use mixin for this, it's also used by MpdState
    def _update_if_changed(self, propname, newval):
        oldval = self.get_property(propname)
        if oldval != newval:
            self.set_property(propname, newval)
