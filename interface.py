import rotaryio
import digitalio
import board

from adafruit_debouncer import Debouncer
from adafruit_ticks import ticks_ms
import neopixel

import event

# pullup buttons are inverted
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

SYNC_CLOCK_IN = board.GP12


class UI(event.EventEmitter):
    def __init__(self):
        super().__init__()

        self.encoder = rotaryio.IncrementalEncoder(*ENCODER_PINS)
        self._last_encoder_position = None
        self._encoder_delta = 0

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

        ext_clock_pin = digitalio.DigitalInOut(SYNC_CLOCK_IN)
        ext_clock_pin.direction = digitalio.Direction.INPUT
        ext_clock_pin.pull = digitalio.Pull.UP
        self.clock_in = Debouncer(ext_clock_pin, 0.005)

    def update(self):
        self.update_encoder()
        self.update_buttons()
        self.sync_clock_in()

    def update_encoder(self):
        self.encoder_button.update()
        position = self.encoder.position

        if None not in (position, self._last_encoder_position):
            self._encoder_delta = position - self._last_encoder_position
        self._last_encoder_position = position

        if self.encoder_button.fell:
            self.emit(event.UI_ENCODER_BUTTON_PRESSED)

        if self._encoder_delta and not any(button.pressing for button in self.buttons):
            self.emit(event.UI_TEMPO_VALUE_CHANGE, self._encoder_delta)

    def update_buttons(self):
        for idx, button in enumerate(self.buttons):
            button.update()

            if button.pressing and self._encoder_delta:
                if self.active_menu != idx:
                    self.active_menu = idx
                    print(f"active menu: {self.active_menu}")
                if idx == 0:
                    self.emit(
                        event.UI_HITS_VALUE_CHANGE, self.active_voice, self._encoder_delta
                    )
                elif idx == 1:
                    self.emit(
                        event.UI_OFFSET_VALUE_CHANGE, self.active_voice, self._encoder_delta
                    )
                elif idx == 2:
                    self.emit(
                        event.UI_STEP_LENGTH_VALUE_CHANGE,
                        self.active_voice,
                        self._encoder_delta,
                    )
                elif idx == 3:
                    self.emit(
                        event.UI_PATTERN_RANDOMIZE, self.active_voice, self._encoder_delta
                    )

            elif button.rose and self.active_menu == idx:
                # show active voice's steps
                self.active_menu = -1

            elif button.rose:
                self.active_voice = idx
                self.emit(event.UI_VOICE_CHANGE, self.active_voice)

    def sync_clock_in(self):
        self.clock_in.update()
        if self.clock_in.fell:
            now = ticks_ms()
            self.emit(event.UI_SYNC_CLOCK_IN, now)


class LED:
    def __init__(self):
        self.tempo_led = digitalio.DigitalInOut(TEMPO_LED_PIN)
        self.tempo_led.direction = digitalio.Direction.OUTPUT
        self.tempo_led.value = True

    def toggle_tempo_led(self, *args):
        self.tempo_led.value = not self.tempo_led.value


class NeoPixel:
    STEP_ON_COLOR = (255, 0, 0)
    BAR_COLOR = (255, 0, 255)
    HEAD_COLOR = (255, 255, 0)

    def __init__(self, step_count=16):
        self.pixels = neopixel.NeoPixel(board.GP2, n=step_count, brightness=0.04)
        self.pixels.fill(0)
        self.step_count = step_count
        self.pattern = [0] * step_count
        self._prev_pixel = self.BAR_COLOR

    def next_step(self, step):
        self.pixels[(step - 1) % self.step_count] = self._prev_pixel
        self._prev_pixel = self.pixels[step]
        self.pixels[step] = self.BAR_COLOR if step == 0 else self.HEAD_COLOR

    def update_pattern(self, pattern):
        self.pattern = pattern
        for step, hit in enumerate(pattern):
            self.pixels[step] = self.STEP_ON_COLOR if hit else 0
        self._prev_pixel = self.pixels[0]