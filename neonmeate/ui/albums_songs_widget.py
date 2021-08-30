from gi.repository import Gtk, GObject

from neonmeate.ui.albums_widget import Albums
from neonmeate.ui.toolkit import glib_main


class AlbumsAndSongs(Gtk.Box):
    __gsignals__ = {
        'playlist-modified': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf,
                 albums_view_options):
        super(AlbumsAndSongs, self).__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._mpdclient = mpdclient
        self._art_cache = art_cache
        self._albums = Albums(
            self._mpdclient,
            self._art_cache,
            placeholder_pixbuf,
            albums_view_options)
        self._albums.connect('album-selected', self._on_album_selected)
        self._albums.connect('playlist-modified', self._on_playlist_modified)
        self.add(self._albums)
        self._albums_list = []
        self._artist_by_name = {}
        self._selected_artist = None
        self._selected_album = None
        self._current_songs = None
        self.show_all()

    def _on_album_selected(self, albums, index):
        album = albums.get_selected_album()
        self._selected_album = album
        self._update_song_info()
        self.clear_songs()
        self._current_songs = Songs(album)
        self._current_songs.show()
        self._songsbox.pack_end(self._current_songs, True, True, 0)
        self.queue_draw()

    def clear(self):
        self._albums.clear()
        self._selected_artist = None
        self._selected_album = None

    def set_artists(self, artists):
        self._albums.set_artists(artists)
        self._artist_by_name = {a.name: a for a in artists}

    def reload(self):
        pass

    def on_artist_selected(self, artist_name):
        if not artist_name or artist_name == self._selected_artist:
            return
        self._selected_artist = None
        self._selected_album = None
        self._current_songs = None
        artist_inst = self._artist_by_name[artist_name]

        @glib_main
        def on_albums(albums):
            self._albums_list.clear()
            self._albums_list.extend(albums)
            self._selected_artist = artist_name
            self._albums.on_artist_selected(artist_name, albums)

        self._mpdclient.find_albums(artist_inst, on_albums)

    def _on_playlist_modified(self, _):
        self.emit('playlist-modified')