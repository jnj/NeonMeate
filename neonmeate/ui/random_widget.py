from gi.repository import Gdk, GObject, Gtk


class RandomWidget(Gtk.Box):
    SIG_RANDOM_ADDED = 'neonmeate_random_added'

    __gsignals__ = {
        SIG_RANDOM_ADDED : (GObject.SignalFlags.RUN_FIRST, None, (str, int))
    }

    def __init__(self):
        super(RandomWidget, self).__init__()
        self.set_spacing(6)
        self._default_num = '50'
        self._number_entry = Gtk.Entry()
        entry_buffer = self._number_entry.get_buffer()
        entry_buffer.set_max_length(3)
        entry_buffer.set_text(self._default_num, 2)
        # self._number_entry.connect('changed', self._on_entry_change)
        self._number_entry.connect('activate', self._on_entry_change)
        self._number_entry.connect('focus_out_event', self._on_unfocus_entry)
        self._combo = Gtk.ComboBoxText()
        self._combo.append('Songs', 'Songs')
        self._combo.append('Artists', 'Artists')
        self._combo.append('Albums', 'Albums')
        self._combo.set_active(0)
        self._add_btn = Gtk.Button()
        self._add_label = Gtk.Label()
        self._add_label.set_text('Add Random')
        self._add_btn.add(self._add_label)
        self.add(self._add_btn)
        self.add(self._number_entry)
        self.add(self._combo)
        self._add_btn.connect('clicked', self._on_add)
        self.show_all()

    def _on_add(self, widget):
        n = int(self._number_entry.get_buffer().get_text())
        item_type = self._combo.get_active_text()
        self.emit(RandomWidget.SIG_RANDOM_ADDED, item_type, n)

    def _on_entry_change(self, entry):
        self._validate_entry()

    def _on_unfocus_entry(self, entry, event):
        self._validate_entry()

    def _validate_entry(self):
        buf = self._number_entry.get_buffer()
        input = buf.get_text()
        trimmed = input.strip()
        if not trimmed:
            buf.set_text(self._default_num, 2)
            return False
        if input.isdecimal():
            return False
        new_input = ''
        for ch in input:
            if ch.isdecimal():
                new_input += ch
        if not new_input:
            buf.set_text(self._default_num, 2)
            return False
        buf.set_text(new_input, len(new_input))
