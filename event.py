UI_PLAY_PAUSE = 0
UI_ENCODER_CHANGED = 1
UI_HITS_VALUE_CHANGE = 2
UI_OFFSET_VALUE_CHANGE = 3
UI_STEP_LENGTH_VALUE_CHANGE = 4
UI_VOICE_CHANGE = 5
UI_TEMPO_VALUE_CHANGE = 6
UI_PATTERN_RANDOMIZE = 7
UI_SYNC_CLOCK_IN = 8
UI_SYNC_CLOCK_OUT = 9
UI_TRIGGER_RESET_PATTERN = 10
UI_SEQUENCE_CHANGE = 11
UI_LOAD_SEQUENCE = 12
UI_SAVE_SEQUENCE = 13
UI_SEQUENCE_MODE = 14

SEQ_STEP_TRIGGER_ON = 15  # (channel, note, velocity)
SEQ_STEP_TRIGGER_OFF = 16  # (channel, note, velocity)
SEQ_STEP_TRIGGER_CHANNELS = 17  # [ch1, ch2, ch3...] where chX is a value 0/1 if channel is triggered or not
SEQ_ACTIVE_STEP = 18
SEQ_TEMPO_CHANGE = 19
SEQ_PATTERN_CHANGE = 20
SEQ_STEP_TRIGGER_MIDI = 21
SEQ_SEQUENCE_SELECT = 22
SEQ_SEQUENCE_SAVING = 23


class EventEmitter:
    def __init__(self):
        self._subscribers = {}

    def register(self, event, callback):
        self._subscribers.setdefault(event, []).append(callback)
    
    def emit(self, event, *args):
        for fn in self._subscribers.get(event, []):
            fn(*args)
