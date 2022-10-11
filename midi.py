import usb_midi
import adafruit_midi

from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

import event


class MIDI(event.EventEmitter):
    def __init__(self):
        super().__init__()
        self.midi = adafruit_midi.MIDI(midi_in=usb_midi.ports[0], midi_out=usb_midi.ports[1])

    def note_on(self, ch, note, velocity):
        self.midi.send(NoteOn(note, velocity, channel=ch))

    def note_off(self, ch, note, velocity):
        self.midi.send(NoteOff(note, velocity, channel=ch))