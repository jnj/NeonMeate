import logging
import os

from gi.repository import Gtk, Gdk, Adw

from .artistsalbums import ArtistsAlbums
from .controls import ControlsBar, ControlButtons, PlayModeButtons
from .nowplaying import NowPlaying
from .playlist import PlaylistContainer
from .settings import SettingsMenu, OutputsSettings
from .toolkit import glib_main
from ..nmpd.mpdlib import MpdHeartbeat as Hb


class App(Gtk.ApplicationWindow):
    Title = 'NeonMeate'

    PlayStatus = {
        'play': (False, False),
        'pause': (True, False),
        'stop': (False, True)
    }

    def __init__(self, app, rng, mpdclient, executor, art_cache, mpd_hb, cfg,
                 configstate, connstatus):
        Gtk.ApplicationWindow.__init__(self, application=app, title=App.Title)
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
        #self._titlebar.set_title("NeonMeate")
        # self._titlebar.set_show_close_button(True)
        self.set_titlebar(self._titlebar)

        self._controlsbar = ControlsBar()
        self._controlsbar.connect(
            PlayModeButtons.SIG_PLAYMODE_TOGGLE,
            self._on_user_mode_toggle
        )
        self._controlsbar.connect(
            ControlButtons.SIG_START_PLAYING,
            self._on_start
        )
        self._controlsbar.connect(
            ControlButtons.SIG_STOP_PLAYING,
            self._on_stop
        )
        self._controlsbar.connect(
            ControlButtons.SIG_TOGGLE_PAUSE,
            self._on_pause
        )
        self._controlsbar.connect(
            ControlButtons.SIG_PREV_SONG,
            self._on_prev_song
        )
        self._controlsbar.connect(
            ControlButtons.SIG_NEXT_SONG,
            self._on_next_song
        )

        self._main_box = Gtk.Box()
        self._main_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_child(self._main_box)
        self._stack = Gtk.Stack()
        self._playlist = PlaylistContainer(mpdclient)
        self._settings = SettingsMenu(executor, configstate, connstatus, cfg)
        self._volume_btn = Gtk.VolumeButton()
        self._volume_btn.connect('value-changed', self._on_volume_change)
        self._settings_btn = Gtk.MenuButton()
        self._connect_handler = self._settings.connect(
            SettingsMenu.SIG_CONNECT_ATTEMPT,
            self.on_connect_attempt
        )
        self._settings.connect(
            SettingsMenu.SIG_UPDATE_REQUESTED,
            self._on_update_request
        )
        self._settings.connect(
            SettingsMenu.SIG_MUSIC_DIR_UPDATED,
            self._on_music_dir
        )
        self._settings.connect(
            SettingsMenu.SIG_OUTPUT_CHANGE,
            self._on_output_change
        )
        self._settings.connect(
            SettingsMenu.SIG_ALBUM_SCALE_CHANGE,
            self._on_album_size_change
        )
        self._settings_btn.set_popover(self._settings)
        self._settings_btn.set_direction(Gtk.ArrowType.NONE)
        Gtk.Settings.get_default().connect(
            'notify::gtk-theme-name',
            self._on_theme_change
        )

        style_ctx = self._settings.get_style_context()
        include_comps = configstate.get_property('albums_include_comps')
        self._artists = ArtistsAlbums(
            mpdclient,
            art_cache,
            cfg,
            style_ctx,
            include_comps
        )
        self._playlist.connect(
            PlaylistContainer.SIG_RANDOM_FILL,
            self._on_random_fill
        )
        self._playlist.connect(
            PlaylistContainer.SIG_PENDING_PLAYLIST_CHG,
            self._on_playlist_pending_change
        )
        self._now_playing = NowPlaying(rng, art_cache, executor, cfg)

        stack_page = self._stack.add_named(self._artists, 'library')
        stack_page.set_icon_name('view-grid-symbolic')

        stack_page = self._stack.add_named(self._playlist, 'playlist')
        stack_page.set_icon_name('view-list-bullet-symbolic')

        stack_page = self._stack.add_named(self._now_playing, 'now_playing')
        stack_page.set_icon_name('emblem-music-symbolic')

        self._stack_switcher = Gtk.StackSwitcher()
        self._stack_switcher.set_stack(self._stack)
        self._stack.connect('notify::visible-child', self._on_stack_change)
        self._spinner = Gtk.Spinner()
        self._spinner.set_vexpand(False)
        self._spinner.set_hexpand(False)
        self._titlebar.pack_start(self._stack_switcher)
        self._titlebar.pack_start(self._spinner)
        self._titlebar.pack_end(self._volume_btn)
        self._titlebar.pack_end(self._settings_btn)
        self._main_box.prepend(self._stack)
        self._main_box.append(self._controlsbar)

        self._mpdhb.connect(Hb.SIG_SONG_ELAPSED, self._on_song_elapsed)
        self._mpdhb.connect(
            Hb.SIG_SONG_PLAYING_STATUS,
            self._on_song_playing_status
        )
        self._mpdhb.connect(Hb.SIG_SONG_CHANGED, self._on_song_changed)
        self._mpdhb.connect(Hb.SIG_NO_SONG, self._no_song)
        self._mpdhb.connect(Hb.SIG_VOL_CHANGE, self._on_volume_sync)
        self._playlist_change_id = self._mpdhb.connect(
            Hb.SIG_PLAYLIST_CHANGED,
            self._update_playlist
        )
        self._mpdhb.connect(Hb.SIG_PLAYBACK_MODE_TOGGLED, self._on_mode_change)
        self._mpdhb.connect(Hb.SIG_UPDATING_DB, self._on_updating_db)
        self._configstate.connect(
            'notify::albums-include-comps',
            self._on_albums_view_change
        )

    def _on_album_size_change(self, widget, size):
        self._artists.on_album_size_change(size)
        self._cfg.save_album_size(size)

    def _on_output_change(self, settings, output_id, enabled):
        self._mpdclient.enable_output(output_id, enabled)

    def _on_albums_view_change(self, state, gparam):
        enabled = state.get_property('albums_include_comps')
        self._artists.on_include_comps_change(enabled)

    def _on_volume_sync(self, hb, volume):
        with self._volume_btn.freeze_notify():
            self._volume_btn.set_value(volume)

    def _on_volume_change(self, button, value):
        self._mpdclient.set_volume(round(value * 100.0))

    def _on_theme_change(self, param1, param2):
        self._artists.on_theme_change()

    def _on_stack_change(self, s, obj):
        pass
        # if 'playlist' == self._stack.get_visible_child_name():
        #     self._stack.child_set_property(
        #         self._playlist,
        #         'needs-attention',
        #         False
        #     )

    def _on_playlist_pending_change(self, widget):
        self._spinner.start()

    def _on_random_fill(self, widget, item_type, n):
        with self._mpdhb.handler_block(self._playlist_change_id):
            self._mpdclient.add_random(item_type, n)

    def _on_music_dir(self, settings, new_dir):
        pass

    def _on_update_request(self, _):
        self._mpdclient.update()

    def on_connect_attempt(self, settings, host, port, should_connect):
        with self._settings.handler_block(self._connect_handler):
            if self._connstatus.is_connected() == should_connect:
                return
            if should_connect:
                if self._playlist_updated:
                    self._playlist_updated = False
                self._mpdclient.connect()
                self._artists.on_mpd_connected(True)
                self._settings.on_outputs(self._mpdclient.get_outputs())
            else:
                self._playlist_updated = False
                self._titlebar.set_title('NeonMeate')
                self._artists.on_mpd_connected(False)
                self._playlist.clear()
                self._now_playing.on_connection_status(False)
                self._mpdclient.disconnect()
                self._settings.on_outputs([])

    def _no_song(self, hb):
        self._on_song_changed(hb, None, None, None, None)

    def _on_user_mode_toggle(self, _, name, is_active):
        self._mpdclient.toggle_play_mode(name, is_active)

    def _on_mode_change(self, hb, name, active):
        self._controlsbar.set_mode(name, active)

    def _on_updating_db(self, obj, value):
        self._artists.on_db_update(value)

    def _update_playlist(self, obj):
        if self._playlist_updated:
            self._artists.on_playlist_modified()

        @glib_main
        def on_current_queue(playqueue):
            self._update_play_queue(playqueue)
            self._playlist_updated = True

        self._mpdclient.playlistinfo(on_current_queue)
        self._spinner.stop()

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
        #self._titlebar.set_title(title_text)
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
