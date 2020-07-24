import json
import os


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
        'media_dir': os.path.join(user_home(), 'Music'),

        # Whether to persist the computed color gradient backgrounds
        # in configuration so that they can be loaded later (this will
        # load them quickly whereas computing the clusters for the
        # gradient can take a little while).
        'cache_backgrounds': True,

        'background_cache': {},

        'mpd': {
            'host': 'localhost',
            'port': 6600
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

    def save(self, file):
        if not os.path.exists(os.path.basename(file)):
            os.makedirs(os.path.basename(file))
        with open(file, 'w') as f:
            json.dump(self._config, f)

    def mpd_host(self):
        return self['mpd']['host']

    def mpd_port(self):
        return self['mpd']['port']

    def get_background(self, artist, album):
        cache_ = self['background_cache']
        if artist in cache_:
            album_art = cache_.get(artist, {}).get(album, None)
            if album_art is not None:
                return album_art
        return None, None

    def save_background(self, artist, album, border, background):
        cache_ = self['background_cache']
        if artist not in cache_:
            cache_[artist] = {}
        cache_[artist][album] = [border.rgb, background.rgb]
