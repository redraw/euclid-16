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
SAMPLE_RATE = 22500
MAX_VOICES = 4

dac = audiopwmio.PWMAudioOut(board.GP15)
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
        print(f"loading {filename}...")
        samples.append(audiocore.WaveFile(open(f"{pack}/{filename}", "rb")))


def play_audio(triggers):
    for ch, trigger in enumerate(triggers):
        if trigger:
            sample = samples[ch]
            mixer.voice[ch].level = 0.8
            mixer.voice[ch].play(sample)


# Print disk info
fs_stat = os.statvfs('/')
print(f"Disk size: {fs_stat[0] * fs_stat[2] / 1024 / 1024} MB")
print(f"Free space: {fs_stat[0] * fs_stat[3] / 1024 / 1024} MB")

# Connect things!
midi = MIDI()
seq = sequencer.EuclideanSequencer(channels=MAX_VOICES, tempo=90)
seq.register(event.SEQ_STEP_TRIGGER_MIDI, midi.trigger_notes)

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
ui.register(event.UI_PLAY_STOP, seq.toggle_play_stop)
ui.register(event.UI_PATTERN_RANDOMIZE, seq.randomize)
ui.register(event.UI_SYNC_CLOCK_IN, seq.trigger_next)
ui.register(event.UI_VOICE_CHANGE, seq.update_active_voice)
ui.register(event.UI_TRIGGER_RESET_PATTERN, seq.reset)
ui.register(event.UI_SEQUENCE_SCHEDULE, seq.schedule_sequence)
ui.register(event.UI_SEQUENCE_SAVE, seq.save_sequence)

leds = interface.LED()
ui.register(event.UI_SEQUENCE_MODE, leds.set_sequence_mode)
seq.register(event.SEQ_SEQUENCE_SELECT, leds.select_sequence)
seq.register(event.SEQ_ACTIVE_STEP, leds.toggle_tempo_led)
seq.register(event.SEQ_ACTIVE_STEP, leds.next_step)
seq.register(event.SEQ_PATTERN_CHANGE, leds.update_pattern)
seq.register(event.SEQ_SEQUENCE_SAVING, leds.set_saving_mode)
# ring = interface.NeoPixel()
# seq.register(event.SEQ_ACTIVE_STEP, ring.next_step)
# seq.register(event.SEQ_PATTERN_CHANGE, ring.update_pattern)

seq.load_sequences()
# seq.randomize()
seq.play()
print(seq)

while True:
    seq.update()
    ui.update()
