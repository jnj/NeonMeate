from gi.repository import GObject, Gtk, Pango, GLib

from neonmeate.ui.controls import NeonMeateButtonBox, ControlButton, \
    PlayModeButton


class SongsMenuButtonBox(NeonMeateButtonBox):
    SIG_ADD_SEL_CLICK = 'neonmeate_add_sel_click'
    SIG_REM_SEL_CLICK = 'neonmeate_rem_sel_click'
    SIG_REP_PLAY_CLICK = 'neonmeate_rep_play_click'

    __gsignals__ = {
        SIG_ADD_SEL_CLICK: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIG_REM_SEL_CLICK: (GObject.SignalFlags.RUN_FIRST, None, ()),
        SIG_REP_PLAY_CLICK: (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    def __init__(self):
        super(SongsMenuButtonBox, self).__init__()
        self._add_sel_btn = ControlButton('list-add-symbolic')
        self._add_sel_btn.set_tooltip_text('Add selected tracks to the queue')
        self.add_button(
            self._add_sel_btn,
            'add-sel',
            SongsMenuButtonBox.SIG_ADD_SEL_CLICK
        )
        self._rem_sel_btn = ControlButton('list-remove-symbolic')
        self._rem_sel_btn.set_tooltip_text(
            'Remove selected tracks from the queue'
        )
        self.add_button(
            self._rem_sel_btn,
            'rem-sel',
            SongsMenuButtonBox.SIG_REM_SEL_CLICK
        )
        self._replace_btn = ControlButton('media-playback-start-symbolic')
        self._replace_btn.set_tooltip_text(
            'Replace queue with selected tracks and play'
        )
        self.add_button(
            self._replace_btn,
            'rep-play',
            SongsMenuButtonBox.SIG_REP_PLAY_CLICK
        )
        for child in self.get_children():
            child.set_can_focus(False)


class SelectSongsButtonBox(NeonMeateButtonBox):
    SIG_TOGGLE_SELECTED = 'neonmeate_toggle_selected'

    __gsignals__ = {
        SIG_TOGGLE_SELECTED: (GObject.SignalFlags.RUN_FIRST, None, (bool,))
    }

    def __init__(self):
        super().__init__()
        self._toggle_selection_btn = PlayModeButton('object-select-symbolic')
        self.add_button(self._toggle_selection_btn, 'toggle-selection', None)
        self._toggle_selection_btn.set_active(True)
        self._toggle_selection_btn.connect('toggled', self._on_toggled)
        self._toggle_selection_btn.set_can_focus(False)

    def _on_toggled(self, btn):
        self.emit(SelectSongsButtonBox.SIG_TOGGLE_SELECTED, btn.get_active())


class SongMenuCheckButton(Gtk.CheckButton):

    def _markup(self):
        pass

    @staticmethod
    def for_disc(song):
        return DiscCheckButton(song)

    @staticmethod
    def for_song(song):
        return SongCheckButton(song)

    def __init__(self, song):
        super().__init__()
        self._song = song
        self.discnum = song.discnum
        self.set_can_focus(False)
        label = Gtk.Label()
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        markup = self._markup()
        label.set_markup(markup)
        label.set_property('xalign', 0)
        label.set_margin_start(8)
        self.set_active(True)
        self.add(label)


class DiscCheckButton(SongMenuCheckButton):
    def __init__(self, song):
        super(DiscCheckButton, self).__init__(song)

    def _markup(self):
        return f'<b>Disc {self._song.discnum}</b>'


class SongCheckButton(SongMenuCheckButton):
    def __init__(self, song):
        super(SongCheckButton, self).__init__(song)

    def _markup(self):
        song = self._song
        esc_title = GLib.markup_escape_text(song.title)
        trackno = song.zero_padded_number()
        time = f'({song.formatted_duration()})'

        if song.is_compilation_track():
            esc_artist = GLib.markup_escape_text(song.artist)
            return f'<small>{trackno}. <b>{esc_artist}</b>' \
                   f' - {esc_title} {time}</small>'
        else:
            return f'<small>{trackno}. {esc_title} {time}</small>'


class SongsMenu(Gtk.Popover):

    def __init__(self, album, mpdclient):
        super(SongsMenu, self).__init__()
        margin = 12
        row_spacing = 10
        max_width = 400
        max_height = 460
        self._selected_songs = []
        self._mpdclient = mpdclient
        self.set_can_focus(False)
        self._album = album

        self._vbox = Gtk.VBox()
        self.add(self._vbox)
        self._vbox.set_halign(Gtk.Align.START)
        self._songslist = Gtk.VBox()
        self._songslist.set_spacing(row_spacing)
        self._songslist.set_halign(Gtk.Align.START)
        self._songslist.set_margin_top(margin)
        self._songslist.set_margin_bottom(margin)
        self._songslist.set_margin_start(margin)
        self._songslist.set_margin_end(margin)
        self._songs = album.sorted_songs()

        self._scrollable = Gtk.ScrolledWindow()
        self._scrollable.set_propagate_natural_height(True)
        self._scrollable.set_propagate_natural_width(True)
        self._scrollable.set_max_content_width(max_width)
        self._scrollable.set_max_content_height(max_height)
        self._scrollable.set_overlay_scrolling(True)
        self._scrollable.set_shadow_type(Gtk.ShadowType.NONE)
        self._scrollable.add(self._songslist)
        multidisc = len(set(song.discnum for song in self._songs)) > 1
        last_discnum = None

        for song in self._songs:
            if multidisc and song.discnum != last_discnum:
                disc_chkbtn = self.__create_disc_entry(song, last_discnum)
                self._songslist.add(disc_chkbtn)

            last_discnum = song.discnum
            checkbox = self.__create_song_entry(song)
            self._songslist.add(checkbox)
            self._selected_songs.append(song)

        self._all_buttons = Gtk.HBox()
        self._btn_box = SongsMenuButtonBox()
        self._btn_box.set_margin_start(margin)
        self._btn_box.set_margin_top(margin)
        self._btn_box.set_margin_bottom(margin)
        self._btn_box.set_margin_end(margin)
        self._btn_box.set_halign(Gtk.Align.START)
        self._btn_box.connect(
            SongsMenuButtonBox.SIG_ADD_SEL_CLICK,
            self._on_add_sel
        )
        self._btn_box.connect(
            SongsMenuButtonBox.SIG_REM_SEL_CLICK,
            self._on_rem_sel
        )
        self._btn_box.connect(
            SongsMenuButtonBox.SIG_REP_PLAY_CLICK,
            self._on_replace
        )
        self._all_buttons.pack_start(self._btn_box, False, False, 0)
        self._toggle_selection_btn = SelectSongsButtonBox()
        self._toggle_selection_btn.set_margin_start(margin)
        self._toggle_selection_btn.set_margin_top(margin)
        self._toggle_selection_btn.set_margin_bottom(margin)
        self._toggle_selection_btn.set_margin_end(margin)
        self._toggle_selection_btn.set_halign(Gtk.Align.END)
        self._toggle_selection_btn.connect(
            SelectSongsButtonBox.SIG_TOGGLE_SELECTED,
            self._on_selection_toggled
        )
        self._all_buttons.pack_end(self._toggle_selection_btn, False, False, 0)
        self._vbox.pack_start(self._all_buttons, False, False, 0)
        self._vbox.pack_end(self._scrollable, True, True, 10)
        self._vbox.show_all()
        for child in self.get_children():
            child.set_can_focus(False)

    def __create_disc_entry(self, song, last_discnum):
        chkbtn = SongMenuCheckButton.for_disc(song)

        if last_discnum is not None:
            chkbtn.set_margin_top(12)

        def toggle_handler(btn, current_disc=song.discnum):
            included = btn.get_active()
            for s in self._songslist.get_children():
                if s.discnum == current_disc:
                    s.set_active(included)

        chkbtn.connect('toggled', toggle_handler)
        return chkbtn

    def __create_song_entry(self, song):
        chkbtn = SongMenuCheckButton.for_song(song)

        def toggle_handler(btn, current_song=song):
            included = current_song in self._selected_songs
            if btn.get_active() and not included:
                self._selected_songs.append(current_song)
            if not btn.get_active() and included:
                self._selected_songs.remove(current_song)

        chkbtn.connect('toggled', toggle_handler)
        return chkbtn

    def _on_selection_toggled(self, btnbox, active):
        for child in self._songslist.get_children():
            if isinstance(child, Gtk.CheckButton):
                if child.get_active() != active:
                    child.set_active(active)

    def _get_selected_songs(self):
        return self._selected_songs

    def _on_replace(self, _):
        self._mpdclient.clear_playlist()
        self._add_selected()
        self._mpdclient.toggle_pause(0)

    def _on_add_sel(self, btn):
        self._add_selected()

    def _add_selected(self):
        songs = self._get_selected_songs()
        ordered = sorted(songs, key=lambda s: (s.discnum, s.number))
        if ordered:
            self._mpdclient.add_songs(ordered)

    def _on_rem_sel(self, btn):
        songs = self._get_selected_songs()
        if songs:
            self._mpdclient.remove_songs(songs)
