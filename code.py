import os
import random
import board
import audiopwmio
# import audiobusio
import audiocore
import audiomixer

from midi import MIDI
import interface
import sequencer
import event

SAMPLE_PACK = "dr55"
SAMPLE_FOLDER = os.listdir("samplepack")
SAMPLE_RATE = 44100
MAX_VOICES = 4

dac = audiopwmio.PWMAudioOut(board.GP13)
# dac = audiobusio.I2SOut(board.GP10, board.GP11, board.GP9)
mixer = audiomixer.Mixer(voice_count=MAX_VOICES, sample_rate=SAMPLE_RATE, channel_count=1)
dac.play(mixer)

samples = []


def load_samplepack(name, randomize=False):
    global samples

    pack = f"samplepack/{name}"
    filenames = os.listdir(pack)

    for idx in range(MAX_VOICES):
        if randomize:
            filename = random.choice(filenames)
        else:
            filename = filenames[idx]
        samples.append(audiocore.WaveFile(open(f"{pack}/{filename}", "rb")))


def play_audio(triggers):
    for ch, trigger in enumerate(triggers):
        if trigger:
            sample = samples[ch]
            mixer.voice[ch].level = 0.1
            mixer.voice[ch].play(sample)


midi = MIDI()

seq = sequencer.EuclideanSequencer(channels=MAX_VOICES, tempo=90)
seq.register(event.SEQ_STEP_TRIGGER_MIDI, midi.trigger_notes)
# seq.register(event.SEQ_STEP_TRIGGER_ON, midi.note_on)
# seq.register(event.SEQ_STEP_TRIGGER_OFF, midi.note_off)

try:
    load_samplepack(SAMPLE_PACK, randomize=False)
    seq.register(event.SEQ_STEP_TRIGGER_CHANNELS, play_audio)
except Exception as e:
    print(e)

ui = interface.UI()
ui.register(event.UI_TEMPO_VALUE_CHANGE, seq.add_tempo)
ui.register(event.UI_HITS_VALUE_CHANGE, seq.update_hits)
ui.register(event.UI_OFFSET_VALUE_CHANGE, seq.update_offsets)
ui.register(event.UI_STEP_LENGTH_VALUE_CHANGE, seq.update_lengths)
ui.register(event.UI_ENCODER_BUTTON_PRESSED, seq.toggle_play_pause)
ui.register(event.UI_PATTERN_RANDOMIZE, seq.randomize)
ui.register(event.UI_SYNC_CLOCK_IN, seq.trigger_next)
ui.register(event.UI_VOICE_CHANGE, seq.update_active_voice)

leds = interface.LED()
seq.register(event.SEQ_ACTIVE_STEP, leds.toggle_tempo_led)
seq.register(event.SEQ_PATTERN_CHANGE, leds.update_pattern)
# ring = interface.NeoPixel()
# seq.register(event.SEQ_ACTIVE_STEP, ring.next_step)
# seq.register(event.SEQ_PATTERN_CHANGE, ring.update_pattern)

seq.randomize()
seq.play()

while True:
    seq.update()
    ui.update()
