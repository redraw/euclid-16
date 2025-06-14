import usb_midi
import event


class MIDI(event.EventEmitter):
    def __init__(self):
        super().__init__()
        self.midi_in, self.midi_out = usb_midi.ports

    def note_on(self, ch, note, velocity):
        self.midi_out.write(bytes([0x90 | (ch & 0xF), note, velocity]))

    def note_off(self, ch, note, velocity):
        self.midi_out.write(bytes([0x80 | (ch & 0xF), note, velocity]))

    def trigger_notes(self, notes):
        for ch, note, velocity in notes:
            if velocity > 0:
                self.note_on(ch, note, velocity)
            else:
                self.note_off(ch, note, velocity)