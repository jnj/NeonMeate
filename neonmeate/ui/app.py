import logging
import os

from gi.repository import Gtk, Gdk

from .artistsalbums import ArtistsAlbums
from .controls import ControlsBar
from .nowplaying import NowPlaying
from .playlist import PlaylistContainer
from .settings import SettingsMenu
from .toolkit import glib_main
from ..nmpd.mpdlib import MpdHeartbeat as Hb


class App(Gtk.ApplicationWindow):
    Title = 'NeonMeate'

    PlayStatus = {
        'play': (False, False),
        'pause': (True, False),
        'stop': (False, True)
    }

    def __init__(self, rng, mpdclient, executor, art_cache, mpd_hb, cfg,
                 configstate, connstatus):
        Gtk.ApplicationWindow.__init__(self, title=App.Title)
        self._connstatus = connstatus
        self._configstate = configstate
        self.name = App.Title
        self.logger = logging.getLogger(__name__)
        self.set_default_icon_name('multimedia-audio-player')
        self._cfg = cfg
        self._executor = executor
        self._mpdhb = mpd_hb
        self._mpdclient = mpdclient
        self._art = art_cache
        self._playlist_updated = False
        self.set_default_size(860, 860)
        self._titlebar = Gtk.HeaderBar()
        self._titlebar.set_title("NeonMeate")
        self._titlebar.set_show_close_button(True)
        self.set_titlebar(self._titlebar)

        self._controlsbar = ControlsBar()
        self._controlsbar.connect(
            'neonmeate_playmode_toggle',
            self._on_user_mode_toggle
        )
        self._controlsbar.connect('neonmeate_start_playing', self._on_start)
        self._controlsbar.connect('neonmeate_stop_playing', self._on_stop)
        self._controlsbar.connect('neonmeate_toggle_pause', self._on_pause)
        self._controlsbar.connect('neonmeate_prev_song', self._on_prev_song)
        self._controlsbar.connect('neonmeate_next_song', self._on_next_song)

        self._main_box = Gtk.VBox()
        self.add(self._main_box)
        self._stack = Gtk.Stack()
        self._playlist = PlaylistContainer(mpdclient)
        self._settings = SettingsMenu(executor, configstate, connstatus, cfg)
        self._settings_btn = Gtk.MenuButton()
        self._connect_handler = self._settings.connect(
            'neonmeate-connect-attempt', self.on_connect_attempt)
        self._settings.connect('neonmeate-update-requested',
                               self._on_update_request)
        self._settings.connect('neonmeate-musicdir-updated', self._on_music_dir)
        self._settings_btn.set_popover(self._settings)
        self._settings_btn.set_direction(Gtk.ArrowType.NONE)
        Gtk.Settings.get_default().connect(
            'notify::gtk-theme-name',
            self._on_theme_change
        )

        style_ctx = self._settings.get_style_context()
        self._artists = ArtistsAlbums(mpdclient, art_cache, cfg, style_ctx)
        self._update_playlist(None)
        self._playlist.connect('neonmeate_random_fill', self._on_random_fill)
        self._now_playing = NowPlaying(rng, art_cache, executor, cfg)
        self._stack.add_named(self._artists, 'library')
        self._stack.add_named(self._playlist, 'playlist')
        self._stack.add_named(self._now_playing, 'now_playing')
        self._stack.child_set_property(
            self._artists,
            'icon-name',
            'view-grid-symbolic'
        )
        self._stack.child_set_property(
            self._playlist,
            'icon-name',
            'view-list-bullet-symbolic'
        )
        self._stack.child_set_property(
            self._now_playing,
            'icon-name',
            'emblem-music-symbolic'
        )
        self._stack_switcher = Gtk.StackSwitcher()
        self._stack_switcher.set_stack(self._stack)
        self._stack.connect('notify::visible-child', self._on_stack_change)
        self._titlebar.pack_start(self._stack_switcher)
        self._titlebar.pack_end(self._settings_btn)
        self._main_box.pack_start(self._stack, True, True, 0)
        self._main_box.pack_end(self._controlsbar, False, False, 0)

        self._mpdhb.connect(Hb.SIG_SONG_ELAPSED, self._on_song_elapsed)
        self._mpdhb.connect(
            Hb.SIG_SONG_PLAYING_STATUS,
            self._on_song_playing_status
        )
        self._mpdhb.connect(Hb.SIG_SONG_CHANGED, self._on_song_changed)
        self._mpdhb.connect(Hb.SIG_NO_SONG, self._no_song)
        self._playlist_change_id = self._mpdhb.connect(
            Hb.SIG_PLAYLIST_CHANGED,
            self._update_playlist
        )
        self._mpdhb.connect(Hb.SIG_PLAYBACK_MODE_TOGGLED, self._on_mode_change)
        self._mpdhb.connect(Hb.SIG_UPDATING_DB, self._on_updating_db)

    def _on_theme_change(self, param1, param2):
        self._artists.on_theme_change()

    def _on_stack_change(self, s, obj):
        if 'playlist' == self._stack.get_visible_child_name():
            self._stack.child_set_property(
                self._playlist,
                'needs-attention',
                False
            )

    def _on_random_fill(self, widget, item_type, n):
        with self._mpdhb.handler_block(self._playlist_change_id):
            self._mpdclient.add_random(item_type, n)

    def _on_music_dir(self, settings, new_dir):
        pass

    def _on_update_request(self, _):
        self._mpdclient.update()

    def on_connect_attempt(self, settings, host, port, should_connect):
        with self._settings.handler_block(self._connect_handler):
            if self._connstatus == should_connect:
                return
            if should_connect:
                self._mpdclient.connect()
                self._artists.on_mpd_connected(True)
            else:
                self._titlebar.set_title('NeonMeate')
                self._artists.on_mpd_connected(False)
                self._playlist.clear()
                self._now_playing.on_connection_status(False)
                self._mpdclient.disconnect()

    def _no_song(self, hb):
        self._on_song_changed(hb, None, None, None, None)

    def _on_user_mode_toggle(self, _, name, is_active):
        self._mpdclient.toggle_play_mode(name, is_active)

    def _on_mode_change(self, hb, name, active):
        self._controlsbar.set_mode(name, active)

    def _on_updating_db(self, obj, value):
        self._artists.on_db_update(value)

    def _update_playlist(self, obj):
        self._artists.on_playlist_modified()

        @glib_main
        def on_current_queue(playqueue):
            self._update_play_queue(playqueue)
            self._playlist_updated = True

        self._mpdclient.playlistinfo(on_current_queue)

    def _update_play_queue(self, playqueue):
        self._playlist.clear()
        artist_elems = [e for e in playqueue if 'artist' in e]
        for elem in artist_elems:
            queue_elem = App._track_details_from_queue_elem(elem)
            artist = queue_elem['artist']
            album = queue_elem['album']
            self._playlist.add_playlist_item(queue_elem)
            cover_path = self._art.resolve_cover_file(
                os.path.dirname(elem['file']))
            self._on_resolved_cover_path(cover_path, artist, album)

    def _on_resolved_cover_path(self, cover_path, artist, album):
        if cover_path is None:
            self.logger.warning(f"Cover not found for {artist} {album}")
        else:
            self._art.fetch(cover_path, None, None)

    @staticmethod
    def _track_details_from_queue_elem(elem):
        """
        Cleans up the playlist entries that come from MPD.
        """
        artist, album, title = elem['artist'], elem['album'], elem['title']
        track = int(elem['track'])
        position = int(elem['pos'])
        duration = float(elem['duration'])
        seconds = int(duration)

        if isinstance(title, list):
            title = ' - '.join(title)

        return {
            'track': track,
            'artist': artist,
            'album': album,
            'title': title,
            'seconds': seconds,
            'position': position
        }

    def _on_song_changed(self, hb, artist, title, album, filepath):
        self.logger.debug(
            f"Song changed. artist={artist}, title={title}, album={album},"
            f" filepath={filepath}")
        title_text = 'NeonMeate'
        if artist and title:
            title_text = f'{artist} - {title}'
        self._titlebar.set_title(title_text)
        if artist is None:
            self._now_playing.clear()
            return
        covpath = self._art.resolve_cover_file(os.path.dirname(filepath))
        if covpath is None:
            self.logger.error(f'File art not found for {filepath}')
        else:
            self._art.fetch(covpath, None, None)
            self._now_playing.on_playing(artist, album, covpath)

    def _on_song_playing_status(self, hb, status):
        paused, stopped = App.PlayStatus.get(status, (False, False))
        self._controlsbar.set_paused(paused, stopped)

    def _on_song_elapsed(self, hb, elapsed, total):
        self._controlsbar.set_song_progress(elapsed, total)

    def _on_start(self, _):
        self._mpdclient.toggle_pause(0)

    def _on_pause(self, _):
        self._mpdclient.toggle_pause(1)

    def _on_stop(self, _):
        self._mpdclient.stop_playing()
        self._controlsbar.set_song_progress(0, 0)

    def _on_prev_song(self, _):
        self._mpdclient.prev_song()

    def _on_next_song(self, _):
        self._mpdclient.next_song()
