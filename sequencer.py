# 6 Aug 2022 - @todbot / Tod Kurt
# 3 Oct 2022 - @redraw
# Based on picostepseq : https://github.com/todbot/picostepseq/
from random import randint
import event

from supervisor import ticks_ms  # thank you dhalbert


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
        delta_t = now - self.last_beat_millis

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
        self.last_beat_millis = (
            ticks_ms() - self.beat_millis
        )  # ensures we start on immediately
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
        super().__init__(*args, step_count=16, **kwargs)
        # self.hits = [
        #     randint(0, len(self.EUC16)) for _ in range(self.channels)
        # ]  # EUC16 idx per channel
        self.hits = [0] * self.channels
        self.offsets = [0] * self.channels  # EUC16 idx per channel
        self.limits = [16] * self.channels  # EUC16 idx per channel

    def __str__(self):
        return "\n".join(
            f"ch: {ch} hits: {self.EUC16[idx]}" for ch, idx in enumerate(self.hits)
        )

    def trigger_step(self):
        self.emit(event.SEQ_ACTIVE_STEP, self.i)
        triggers = [0] * self.channels

        for ch, idx in enumerate(self.hits):
            hit = self.EUC16[idx][self.i]
            prev_hit = self.EUC16[idx][(self.i - 1) % self.step_count]
            triggers[ch] = hit

            if hit:
                self.emit(event.SEQ_STEP_TRIGGER_ON, ch, ch, 127)
            elif prev_hit == 1:
                self.emit(event.SEQ_STEP_TRIGGER_OFF, ch, ch, 127)

        self.emit(event.SEQ_STEP_TRIGGER_ALL, triggers)

    def update_hits(self, ch, delta):
        self.hits[ch] = max(0, min(self.hits[ch] + delta, self.step_count))
        print("-")
        print(self)
