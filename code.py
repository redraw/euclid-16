import gc
import audiocore
import board
import audiobusio
import audiomixer

import interface
from midi import MIDI
import sequencer
import event

audio = audiobusio.I2SOut(board.GP10, board.GP11, board.GP9)
mixer = audiomixer.Mixer(voice_count=4, sample_rate=44100, channel_count=1)
audio.play(mixer)

kick = audiocore.WaveFile(open("dr55/kick.wav", "rb"))
hh = audiocore.WaveFile(open("dr55/hat.wav", "rb"))
rim = audiocore.WaveFile(open("dr55/rim.wav", "rb"))
snare = audiocore.WaveFile(open("dr55/snare.wav", "rb"))

samples = [
    kick,
    hh,
    rim,
    snare,
]


def play_audio(triggers):
    gc.collect()

    for ch, trigger in enumerate(triggers):
        if trigger:
            sample = samples[ch]
            mixer.voice[ch].level = 0.1
            mixer.voice[ch].play(sample)
        else:
            mixer.voice[ch].stop()


midi = MIDI()

seq = sequencer.EuclideanSequencer(channels=len(samples))
seq.register(event.SEQ_STEP_TRIGGER_ON, midi.note_on)
seq.register(event.SEQ_STEP_TRIGGER_OFF, midi.note_off)
seq.register(event.SEQ_STEP_TRIGGER_ALL, play_audio)
seq.play()

ui = interface.UI()
ui.register(event.UI_TEMPO_VALUE_CHANGE, seq.add_tempo)
ui.register(event.UI_HITS_VALUE_CHANGE, seq.update_hits)
ui.register(event.UI_ENCODER_BUTTON_PRESSED, seq.toggle_play_pause)

leds = interface.LED()
seq.register(event.SEQ_ACTIVE_STEP, leds.toggle_tempo_led)

while True:
    ui.update()
    seq.update()
