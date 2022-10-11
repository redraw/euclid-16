# 6 Aug 2022 - @todbot / Tod Kurt
# 3 Oct 2022 - @redraw
# Based on picostepseq : https://github.com/todbot/picostepseq/
from random import randint
import event

from adafruit_ticks import ticks_ms, ticks_diff


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
        self.seqno = seqno  # an 'id' of what sequence it's currently playing

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

    def toggle_play_pause(self):
        if self.playing:
            print("Sequencer stopped.")
            self.pause()
        else:
            print("Sequencer playing.")
            self.play()

    def stop(self):  # FIXME: what about pending note
        self.playing = False
        self.i = 0
        self.last_beat_millis = 0

    def pause(self):
        self.playing = False

    def play(self):
        self.last_beat_millis = ticks_ms() - self.beat_millis
        self.playing = True


class EuclideanSequencer(StepSequencer):
    # pre-calculated euclidean beats
    EUC16 = (
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
        (1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0),
        (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0),
        (1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0),
        (1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0),
        (1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0),
        (1, 0, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0),
        (1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0),
        (1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0),
        (1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1),
        (1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1),
        (1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 0, 1, 1),
        (1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1, 1, 1),
        (1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1),
        (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0),
        (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.euc_idxs = [0] * self.channels  # EUC16 idx per channel
        self.offsets = [0] * self.channels  # offset value per channel
        self.lengths = [self.step_count] * self.channels  # step length value per channel
        self.patterns = [[0] * self.step_count for _ in range(self.channels)]  # calculated patterns (EUC16 + offset + length)
        self.active_ch = 0

    def __str__(self):
        return "\n".join(
            f"ch: {ch} pattern: {pattern}" for ch, pattern in enumerate(self.patterns)
        )

    def randomize(self, *args):
        self.euc_idxs = [
            randint(0, len(self.EUC16) - 1) for _ in range(self.channels)
        ] 
        
        for ch in range(self.channels):
            self._calculate_pattern(ch)

        print("-")
        print(self)

    @staticmethod
    def _rotate(arr, n):
        return arr[n:] + arr[:n]

    def _calculate_pattern(self, ch):
        idx = self.euc_idxs[ch]
        rotated = self._rotate(self.EUC16[idx], self.offsets[ch])
        pattern = tuple(
            1 if hit and i <= self.lengths[ch] else 0 
            for i, hit in enumerate(rotated)
        )
        self.patterns[ch] = pattern

        if ch == self.active_ch:
            self.emit(event.SEQ_PATTERN_CHANGE, pattern)
    
    def trigger_step(self):
        self.emit(event.SEQ_ACTIVE_STEP, self.i)
        triggers = [0] * self.channels

        for ch, pattern in enumerate(self.patterns):
            hit = triggers[ch] = pattern[self.i]
            prev_hit = pattern[(self.i - 1) % self.step_count]

            if hit:
                self.emit(event.SEQ_STEP_TRIGGER_ON, ch, ch, 127)
            if prev_hit == 1:
                self.emit(event.SEQ_STEP_TRIGGER_OFF, ch, ch, 127)

        self.emit(event.SEQ_STEP_TRIGGER_CHANNELS, triggers)
    
    def update_hits(self, ch, delta):
        """set EUC16 beat index per channel, delta might be -1 or 1"""
        self.active_ch = ch
        self.euc_idxs[ch] = max(0, min(self.euc_idxs[ch] + delta, len(self.EUC16) - 1))
        self._calculate_pattern(ch)
        print("-")
        print(self)

    def update_offsets(self, ch, delta):
        """set offset per channel between -step_count to +step_count, delta might be -1 or 1"""
        self.active_ch = ch
        self.offsets[ch] = (self.offsets[ch] - delta) % self.step_count
        self._calculate_pattern(ch)
        print("-")
        print(self)

    def update_lengths(self, ch, delta):
        """set step length per channel between 0 and step_count, delta might be -1 or 1"""
        self.active_ch = ch
        self.lengths[ch] = max(0, min(self.lengths[ch] + delta, self.step_count))
        self._calculate_pattern(ch)
        print("-")
        print(self)