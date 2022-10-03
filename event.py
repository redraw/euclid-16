UI_ENCODER_BUTTON_PRESSED = 0
UI_ENCODER_CHANGED = 1
UI_HITS_VALUE_CHANGE = 2
UI_OFFSET_VALUE_CHANGE = 3
UI_STEP_LENGTH_VALUE_CHANGE = 4
UI_VOICE_CHANGE = 5
UI_TEMPO_VALUE_CHANGE = 6

SEQ_STEP_TRIGGER_ON = 7
SEQ_STEP_TRIGGER_OFF = 8
SEQ_STEP_TRIGGER_ALL = 9
SEQ_ACTIVE_STEP = 10


class EventEmitter:
    def __init__(self):
        self._subscribers = {}

    def register(self, event, callback):
        self._subscribers.setdefault(event, []).append(callback)
    
    def emit(self, event, *args):
        for fn in self._subscribers.get(event, []):
            fn(*args)
