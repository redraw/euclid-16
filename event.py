UI_ENCODER_BUTTON_PRESSED = 0
UI_ENCODER_CHANGED = 1
UI_HITS_VALUE_CHANGE = 2
UI_OFFSET_VALUE_CHANGE = 3
UI_STEP_LENGTH_VALUE_CHANGE = 4
UI_VOICE_CHANGE = 5
UI_TEMPO_VALUE_CHANGE = 6
UI_PATTERN_RANDOMIZE = 7
UI_SYNC_CLOCK_IN = 8
UI_SYNC_CLOCK_OUT = 9

SEQ_STEP_TRIGGER_ON = 10  # (channel, note, velocity)
SEQ_STEP_TRIGGER_OFF = 11  # (channel, note, velocity)
SEQ_STEP_TRIGGER_CHANNELS = 12  # [ch1, ch2, ch3...] where chX is a value 0/1 if channel is triggered or not
SEQ_ACTIVE_STEP = 13
SEQ_TEMPO_CHANGE = 14
SEQ_PATTERN_CHANGE = 15
SEQ_STEP_TRIGGER_MIDI = 16


class EventEmitter:
    def __init__(self):
        self._subscribers = {}

    def register(self, event, callback):
        self._subscribers.setdefault(event, []).append(callback)
    
    def emit(self, event, *args):
        for fn in self._subscribers.get(event, []):
            fn(*args)
