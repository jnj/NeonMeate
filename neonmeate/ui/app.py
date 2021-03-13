import logging
import os

from gi.repository import Gtk

from .artistsalbums import ArtistsAlbums
from .controls import ControlButtons, PlayModeButtons
from .nowplaying import NowPlaying
from .playlist import PlaylistContainer
from .songprogress import SongProgress
from .toolkit import gtk_main
from .settings import SettingsMenu


# noinspection PyUnresolvedReferences,PyArgumentList
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
        # TODO pick up this size from config
        self.set_default_size(860, 860)
        self._titlebar = Gtk.HeaderBar()
        self._titlebar.set_title("NeonMeate")
        self._titlebar.set_show_close_button(True)
        self.set_titlebar(self._titlebar)
        self._ctrl_btns = ControlButtons()
        self._mode_btns = PlayModeButtons()
        self._progress = SongProgress()
        self._actionbar = Gtk.ActionBar()
        self._actionbar.pack_start(self._ctrl_btns)
        self._actionbar.pack_start(self._progress)
        self._actionbar.pack_start(self._mode_btns)
        self._main_box = Gtk.VBox()
        self.add(self._main_box)
        self._stack = Gtk.Stack()
        self._artists = ArtistsAlbums(mpdclient, art_cache, cfg)
        self._playlist = PlaylistContainer(mpdclient)
        self._update_playlist(None)
        self._playlist.connect('neonmeate_random_fill', self._on_random_fill)
        self._now_playing = NowPlaying(rng, art_cache, executor, cfg)
        self._stack.add_named(self._artists, 'library')
        self._stack.add_named(self._playlist, 'playlist')
        self._stack.add_named(self._now_playing, 'now_playing')
        self._stack.child_set_property(
            self._artists,
            'icon-name',
            'emblem-music-symbolic'
        )
        self._stack.child_set_property(
            self._playlist,
            'icon-name',
            'view-list-symbolic'
        )
        self._stack.child_set_property(
            self._now_playing,
            'icon-name',
            'mediaplayer-app-symbolic'
        )
        self._stack_switcher = Gtk.StackSwitcher()
        self._stack_switcher.set_stack(self._stack)
        self._stack.connect('notify::visible-child', self._on_stack_change)
        self._titlebar.pack_start(self._stack_switcher)
        self._settings_btn = Gtk.MenuButton()
        self._settings = SettingsMenu(executor, configstate, connstatus)
        self._connect_handler = self._settings.connect(
            'neonmeate-connect-attempt', self.on_connect_attempt)
        self._settings.connect('neonmeate-update-requested',
                               self._on_update_request)
        self._settings.connect('neonmeate-musicdir-updated', self._on_music_dir)
        self._settings_btn.set_popover(self._settings)
        self._settings_btn.set_direction(Gtk.ArrowType.NONE)

        self._titlebar.pack_end(self._settings_btn)
        self._main_box.pack_start(self._stack, True, True, 0)
        self._main_box.pack_end(self._actionbar, False, False, 0)

        self._ctrl_btns.connect('neonmeate_stop_playing', self._on_stop)
        self._ctrl_btns.connect('neonmeate_start_playing', self._on_start)
        self._ctrl_btns.connect('neonmeate_toggle_pause', self._on_pause)
        self._ctrl_btns.connect('neonmeate_prev_song', self._on_prev_song)
        self._ctrl_btns.connect('neonmeate_next_song', self._on_next_song)

        self._mode_btns.subscribe_to_signal(
            'neonmeate_playmode_toggle', self._on_user_mode_toggle
        )

        self._mpdhb.connect('song_elapsed', self._on_song_elapsed)
        self._mpdhb.connect('song_playing_status', self._on_song_playing_status)
        self._mpdhb.connect('song_changed', self._on_song_changed)
        self._mpdhb.connect('no_song', self._no_song)
        self._playlist_change_id = self._mpdhb.connect(
            'playlist-changed',
            self._update_playlist
        )
        self._mpdhb.connect('playback-mode-toggled', self._on_mode_change())
        self._mpdhb.connect('updatingdb', self._on_updating_db)

    def _on_stack_change(self, s, obj):
        if 'playlist' == self._stack.get_visible_child_name():
            self._stack.child_set_property(
                self._playlist,
                'needs-attention',
                False
            )

    def _on_random_fill(self, _):
        with self._mpdhb.handler_block(self._playlist_change_id):
            self._artists.on_random_fill()

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

    def _on_mode_change(self):
        def handler(_, name, is_active):
            self._mode_btns.on_mode_change(name, is_active)

        return handler

    def _on_updating_db(self, obj, value):
        self._artists.on_db_update(value)

    def _update_playlist(self, obj):

        @gtk_main
        def on_current_queue(playqueue):
            self._update_play_queue(playqueue)
            # only set needs-attention after the first time
            # we've updated the playlist
            if self._playlist_updated and playqueue:
                self._stack.child_set_property(
                    self._playlist,
                    'needs-attention',
                    True
                )
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
            print(f"Cover not found for {artist} {album}")
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
        self.logger.info(
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
        self._ctrl_btns.set_paused(paused, stopped)

    def _on_song_elapsed(self, hb, elapsed, total):
        self._progress.set_elapsed(elapsed, total)

    def _on_start(self, widget):
        self._mpdclient.toggle_pause(0)

    def _on_pause(self, widget):
        self._mpdclient.toggle_pause(1)

    def _on_stop(self, widget):
        self._mpdclient.stop_playing()
        self._progress.set_fraction(0)

    def _on_prev_song(self, widget):
        self._mpdclient.prev_song()

    def _on_next_song(self, widget):
        self._mpdclient.next_song()
