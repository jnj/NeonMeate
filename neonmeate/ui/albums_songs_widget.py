from gi.repository import Gtk, GObject

from neonmeate.ui.albums_widget import Albums
from neonmeate.ui.toolkit import glib_main


class AlbumsAndSongs(Gtk.Box):

    def __init__(self, mpdclient, art_cache, placeholder_pixbuf,
                 albums_view_options, border_style_context):
        super(AlbumsAndSongs, self).__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._mpdclient = mpdclient
        self._art_cache = art_cache
        self._albums = Albums(
            self._mpdclient,
            self._art_cache,
            placeholder_pixbuf,
            albums_view_options,
            border_style_context
        )
        self._albums.connect(
            Albums.SIG_ALBUM_SELECTED,
            self._on_album_selected
        )
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

    def on_album_size_change(self, size):
        self._albums.on_album_size(size)

    def on_theme_change(self):
        self._albums.on_theme_change()

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
