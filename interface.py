import rotaryio
import digitalio
import board
from adafruit_debouncer import Debouncer

import event

Debouncer.pressing = property(lambda self: not self.value)

BUTTON_PINS = (
    board.GP21,
    board.GP20,
    board.GP19,
    board.GP18,
)

ENCODER_PINS = (
    board.GP17,
    board.GP16,
)

ENCODER_BUTTON_PIN = board.GP22
TEMPO_LED_PIN = board.GP26


class UI(event.EventEmitter):
    def __init__(self):
        self.encoder = rotaryio.IncrementalEncoder(*ENCODER_PINS)
        self._last_encoder_position = None

        encoder_button_pin = digitalio.DigitalInOut(ENCODER_BUTTON_PIN)
        encoder_button_pin.direction = digitalio.Direction.INPUT
        encoder_button_pin.pull = digitalio.Pull.UP
        self.encoder_button = Debouncer(encoder_button_pin)

        self.buttons = []
        for pin in BUTTON_PINS:
            sw = digitalio.DigitalInOut(pin)
            sw.direction = digitalio.Direction.INPUT
            sw.pull = digitalio.Pull.UP
            button = Debouncer(sw)
            self.buttons.append(button)

        self.active_voice = 0
        self.active_menu = -1

        super().__init__()

    def update(self):
        # encoder
        self.encoder_button.update()

        position = self.encoder.position
        encoder_delta = 0

        if None not in (position, self._last_encoder_position):
            encoder_delta = position - self._last_encoder_position
        self._last_encoder_position = position

        if self.encoder_button.fell:
            self.emit(event.UI_ENCODER_BUTTON_PRESSED)

        # buttons
        for idx, button in enumerate(self.buttons):
            button.update()

            if button.pressing and encoder_delta:
                if self.active_menu != idx:
                    self.active_menu = idx
                    print(f"active menu: {self.active_menu}")
                if idx == 0:
                    self.emit(
                        event.UI_HITS_VALUE_CHANGE, self.active_voice, encoder_delta
                    )
                elif idx == 1:
                    self.emit(
                        event.UI_OFFSET_VALUE_CHANGE, self.active_voice, encoder_delta
                    )
                elif idx == 2:
                    self.emit(
                        event.UI_STEP_LENGTH_VALUE_CHANGE,
                        self.active_voice,
                        encoder_delta,
                    )

            elif button.rose and self.active_menu == idx:
                # show active voice's steps
                self.active_menu = -1

            elif button.rose:
                self.active_voice = idx
                self.emit(event.UI_VOICE_CHANGE, self.active_voice)

        if encoder_delta and not any(button.pressing for button in self.buttons):
            self.emit(event.UI_TEMPO_VALUE_CHANGE, encoder_delta)


class Display:
    def __init__(self):
        self.tempo_led = digitalio.DigitalInOut(TEMPO_LED_PIN)
        self.tempo_led.direction = digitalio.Direction.OUTPUT
        self.tempo_led.value = False

    def toggle_led(self, *args):
        self.tempo_led.value = not self.tempo_led.value
