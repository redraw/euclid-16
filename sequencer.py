# 6 Aug 2022 - @todbot / Tod Kurt
# 3 Oct 2022 - @redraw
# Based on picostepseq : https://github.com/todbot/picostepseq/
from random import randint
import os
import json

from adafruit_ticks import ticks_ms, ticks_diff

import event

SEQUENCES_FILE = "sequences.json"
MAX_SEQUENCES = 16


class StepSequencer(event.EventEmitter):
    def __init__(self, step_count=16, tempo=120, playing=False, channels=6, seqno=0):
        super().__init__()
        self.ext_trigger = False  # midi clocked or not
        self.steps_per_beat = 4  # 16th note
        self.channels = channels  # aka. voices
        self.step_count = step_count
        self.i = 0  # where in the sequence we currently are
        self.set_tempo(tempo)
        self.last_beat_millis = ticks_ms()  # 'tempo' in our native tongue
        self.playing = playing  # is sequence running or not (but use .play()/.pause())

    def set_tempo(self, tempo):
        """Sets the internal tempo. beat_millis is 1/16th note time in milliseconds"""
        self.tempo = tempo
        self.beat_millis = 60_000 // self.steps_per_beat // tempo
        self.emit(event.SEQ_TEMPO_CHANGE, tempo)

    def add_tempo(self, delta):
        self.set_tempo(self.tempo + delta)

    def trigger_next(self, now):
        """Trigger next step in sequence (and thus make externally triggered)"""
        self.ext_trigger = True
        self.trigger(now, self.beat_millis)

    def trigger(self, now, delta_t):
        if not self.playing:
            return
        fudge = 0  # seems more like 3-10

        # go to next step in sequence, get new note
        self.i = (self.i + 1) % self.step_count
        self.trigger_step()

        # calculate next note timing and held note timing
        err_t = delta_t - self.beat_millis  # how much we are over
        # print("err_t:",self.i, err_t, self.beat_millis)
        self.last_beat_millis = now - err_t - fudge  # adjust for our overage

    def trigger_step(self):
        return NotImplemented

    def update(self):
        """Update state of sequencer. Must be called regularly in main"""
        now = ticks_ms()
        # delta_t = now - self.last_beat_millis
        delta_t = ticks_diff(now, self.last_beat_millis)

        # if time for new note, trigger it
        if delta_t >= self.beat_millis:
            if not self.ext_trigger:
                self.trigger(now, delta_t)
            else:
                # fall back to internal triggering if not externally clocked for a while
                if delta_t > self.beat_millis * 4:
                    self.ext_trigger = False
                    print("Turning EXT TRIGGER off")

    def toggle_play_stop(self):
        if self.playing:
            print("Sequencer stopped.")
            self.stop()
        else:
            print("Sequencer playing.")
            self.play()

    def stop(self):
        self.playing = False
        self.i = 15
        self.last_beat_millis = 0

    def pause(self):
        self.playing = False

    def play(self):
        self.last_beat_millis = ticks_ms() - self.beat_millis
        self.playing = True


class EuclideanSequencer(StepSequencer):
    # Pre-calculated euclidean patterns
    # Each pattern is represented as a 16-bit integer
    # Bit 1 is hit, bit 0 is silence
    # LSB: step 0
    # MSB: step 16
    EUC16 = (
        0b0000000000000000,
        0b0000000000000001,
        0b0000000100000001,
        0b0000010000100001,
        0b0001000100010001,
        0b0001001001001001,
        0b0010100100101001,
        0b0101010010101001,
        0b0101010101010101,
        0b0101011010101101,
        0b1010110110101101,
        0b1101101101101101,
        0b1101110111011101,
        0b1111011110111101,
        0b1111110111111101,
        0b0111111111111111,
        0b1111111111111111,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.step_count <= 16, "this sequencer supports up to 16 steps!"
        self.sequences = [0] * MAX_SEQUENCES
        self.reset()
        self.sequence_idx = 0
        self.next_sequence_idx = 0

    def reset(self):
        self.euc_idxs = bytearray(self.channels)  # EUC16 idx per channel
        self.offsets = bytearray(self.channels)  # offset value per channel
        self.lengths = bytearray(self.step_count for _ in range(self.channels))  # step length value per channel
        self.patterns = [0b0 for _ in range(self.channels)]  # calculated patterns (EUC16 + offset + length)
        self._audio_triggers = bytearray(self.channels)
        self._midi_notes = []
        self.active_ch = 0

    def __str__(self):
        return "\n".join(
            f"ch: {ch} pattern: {bin(pattern)}" for ch, pattern in enumerate(self.patterns)
        )

    def randomize(self, *args):
        for ch in range(self.channels):
            self.euc_idxs[ch] = randint(0, len(self.EUC16) - 1)
            self.offsets[ch] = randint(0, self.step_count)
            self.lengths[ch] = randint(self.step_count // 2, self.step_count)
            self._calculate_pattern(ch)

    def _calculate_pattern(self, ch):
        idx = self.euc_idxs[ch]
        pattern = self.EUC16[idx]
        pattern = self._shrink(pattern, self.lengths[ch])
        pattern = self._rotate(pattern, self.offsets[ch])
        self.patterns[ch] = pattern

        if ch == self.active_ch:
            self.emit(event.SEQ_PATTERN_CHANGE, pattern)
    
    @staticmethod
    def _shrink(pattern, n):
        return pattern & (2 ** n - 1)

    @staticmethod
    def _rotate(pattern, n):
        """
        Taking advantage of the RPi Pico 32-bit CPU,
        we can perform a 32-bit bitwise operation
        to circular shift the 16-bit pattern.
        """
        n %= 16
        return (pattern >> n) | (pattern << 16 - n) & 0xFFFF

    def trigger_step(self):
        self.emit(event.SEQ_ACTIVE_STEP, self.i)
        self._audio_triggers = bytearray(self.channels)
        self._midi_notes = []

        # load next sequence at step 0
        if self.i == 0 and self.sequence_idx != self.next_sequence_idx:
            self.sequence_idx = self.next_sequence_idx
            self.load_sequence()

        # calculate audio/midi triggers for step
        for ch, pattern in enumerate(self.patterns):
            step = self.i
            hit = self._audio_triggers[ch] = (pattern & (2 ** step)) > 0
            prev_two_step = (self.i - 2) % self.step_count
            prev_two_hit = (pattern & (2 ** prev_two_step)) > 0

            if prev_two_hit:
                self._midi_notes.append((ch, ch, 0))
            if hit:
                self._midi_notes.append((ch, ch, 127))

        self.emit(event.SEQ_STEP_TRIGGER_MIDI, self._midi_notes)
        self.emit(event.SEQ_STEP_TRIGGER_CHANNELS, self._audio_triggers)
    
    def update_active_voice(self, ch):
        self.active_ch = ch
        self._calculate_pattern(ch)
   
    def update_hits(self, ch, delta):
        """set EUC16 beat index per channel, delta might be -1 or 1"""
        self.euc_idxs[ch] = max(0, min(self.euc_idxs[ch] + delta, len(self.EUC16) - 1))
        self._calculate_pattern(ch)

    def update_offsets(self, ch, delta):
        """set offset per channel between -step_count to +step_count, delta might be -1 or 1"""
        self.offsets[ch] = (self.offsets[ch] - delta) % self.step_count
        self._calculate_pattern(ch)

    def update_lengths(self, ch, delta):
        """set step length per channel between 0 and step_count, delta might be -1 or 1"""
        self.lengths[ch] = max(0, min(self.lengths[ch] + delta, self.step_count))
        self._calculate_pattern(ch)

    def load_sequences(self):
        try:
            os.stat(SEQUENCES_FILE)
        except OSError:
            self.save_sequence()

        with open(SEQUENCES_FILE) as f:
            self.sequences = json.load(f)
        
        self.load_sequence()

    def schedule_sequence(self, delta=0):
        self.next_sequence_idx = (self.next_sequence_idx + delta) % self.step_count
        self.emit(event.SEQ_SEQUENCE_SELECT, self.next_sequence_idx)

        if not self.playing:
            self.sequence_idx = self.next_sequence_idx
            self.load_sequence()
        
    def load_sequence(self):
        print(f"loading {self.sequence_idx}...")
        sequence = self.sequences[self.sequence_idx]

        # empty sequence check
        if not sequence:
            self.reset()
            return

        self.euc_idxs = bytearray(sequence["euc_idxs"])
        self.offsets = bytearray(sequence["offsets"])
        self.lengths = bytearray(sequence["lengths"])

        for ch in range(self.channels):
            self._calculate_pattern(ch)
        
    def save_sequence(self):
        was_playing = self.playing

        if was_playing:
            self.pause()

        print(f"saving {self.sequence_idx}...")
        self.emit(event.SEQ_SEQUENCE_SAVING, True)
        self.sequences[self.sequence_idx] = {
            "euc_idxs": list(self.euc_idxs),
            "offsets": list(self.offsets),
            "lengths": list(self.lengths),
        }

        with open(SEQUENCES_FILE, "wb") as f:
            json.dump(self.sequences, f)

        print(f"saved.")
        self.emit(event.SEQ_SEQUENCE_SAVING, False)

        if was_playing:
            self.play()
