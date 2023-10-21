from gi.repository import Gtk, Gdk, GdkPixbuf

from .albums_songs_widget import AlbumsAndSongs
from .artists_widget import ArtistsWidget
from neonmeate.ui.toolkit import TimedInfoBar, \
    BooleanRef


class AlbumViewOptions:
    def __init__(self):
        self.border_width = 4
        self.album_size = 120
        self.col_spacing = 50
        self.row_spacing = 30


# noinspection PyUnresolvedReferences
class ArtistsAlbums(Gtk.Overlay):

    def __init__(self, mpdclient, art, cfg, style_context, include_comps):
        super(ArtistsAlbums, self).__init__()
        album_view_opts = AlbumViewOptions()
        album_view_opts.album_size = cfg.album_size()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self._box)
        self._infobar = TimedInfoBar()
        self._infobar.set_halign(Gtk.Align.START)
        self._infobar.set_valign(Gtk.Align.START)
        self.add_overlay(self._infobar)
        # self.pack_start(self._infobar, False, False, 0)
        self._update_pending = BooleanRef()
        display = Gdk.Display.get_default()
        icon_theme = Gtk.IconTheme.get_for_display(display)
        placeholder_icon = icon_theme.lookup_icon(
                'media-optical-cd-audio-symbolic',
                [],
                album_view_opts.album_size,
                1, 0, 0)

        self._album_placeholder_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            placeholder_icon.get_file().get_path(),
            album_view_opts.album_size,
            album_view_opts.album_size,
            False,
        )

        self._art = art
        self._cfg = cfg
        self._mpdclient = mpdclient
        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._artists = ArtistsWidget(mpdclient, include_comps)
        self._artists.connect(
            ArtistsWidget.SIG_ARTIST_SELECTED,
            self._on_artist_clicked
        )
        self._artists.connect(
            ArtistsWidget.SIG_ARTISTS_LOADED,
            self._on_artists_loaded
        )

        columns.prepend(self._artists)
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        columns.prepend(separator)

        # self._albums_songs = AlbumsAndSongs(
        #     self._mpdclient,
        #     self._art,
        #     self._album_placeholder_pixbuf,
        #     album_view_opts,
        #     style_context
        # )

        #columns.append(self._albums_songs)
        self._box.append(columns)
        # self.show_all()

    def on_album_size_change(self, size):
        self._albums_songs.on_album_size_change(size)

    def on_include_comps_change(self, enabled):
        self._artists.on_include_comps_change(enabled)

    def on_theme_change(self):
        self._albums_songs.on_theme_change()

    def on_playlist_modified(self):
        pass

    def _on_artists_loaded(self, _, done):
        if done:
            self._albums_songs.set_artists(self._artists.get_artists())

    def on_mpd_connected(self, connected):
        if connected:
            self._reload()
        if not connected:
            self._artists.clear()
            self._albums_songs.clear()

    def on_db_update(self, is_updating):
        pending = self._update_pending.current()
        changed = self._update_pending.update(is_updating)
        if pending and changed:
            self._reload()

    def _reload(self):
        self._artists.reload_artists()
        self._albums_songs.reload()

    def _on_artist_clicked(self, col_widget, selected_value):
        self._albums_songs.on_artist_selected(selected_value)
