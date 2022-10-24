import rotaryio
import bitbangio
import digitalio
import board

from adafruit_debouncer import Debouncer
from adafruit_ticks import ticks_ms, ticks_diff
import neopixel
import adafruit_74hc595

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

ENCODER_BUTTON_PIN = board.GP26
TEMPO_LED_PIN = board.GP22

LEDS_595_LATCH_PIN = board.GP2
LEDS_595_SCLK = board.GP3
LEDS_595_DATA = board.GP4

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

        self._reset_threshold = ticks_ms()

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
        now = ticks_ms()

        for idx, button in enumerate(self.buttons):
            button.update()

            if button.pressing and self._encoder_delta:
                if self.active_menu != idx:
                    self.active_menu = idx
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

        if all(button.pressing for button in self.buttons) and ticks_diff(now, self._reset_threshold) > 500:
            self._reset_threshold = now
            self.emit(event.UI_TRIGGER_RESET_PATTERNS)

    def sync_clock_in(self):
        self.clock_in.update()
        if self.clock_in.fell:
            now = ticks_ms()
            self.emit(event.UI_SYNC_CLOCK_IN, now)


class LED:
    def __init__(self):
        self.tempo_pin = digitalio.DigitalInOut(TEMPO_LED_PIN)
        self.tempo_pin.direction = digitalio.Direction.OUTPUT
        self.tempo_pin.value = False

        # using bitbangio as I messed up the default SPI pins
        spi = bitbangio.SPI(LEDS_595_SCLK, MOSI=LEDS_595_DATA)
        latch_pin = digitalio.DigitalInOut(LEDS_595_LATCH_PIN)
        self.sr = adafruit_74hc595.ShiftRegister74HC595(spi, latch_pin, number_of_shift_registers=2)

        self.pattern = 0b0
    
    def clear_steps(self):
        self.sr.gpio = bytearray((0, 0))

    def toggle_tempo_led(self, *args):
        self.tempo_pin.value = not self.tempo_pin.value

    def next_step(self, step):
        """sum up pattern and current step in an OR operation"""
        value = self.pattern | 2 ** step
        self._update_leds(value)

    def update_pattern(self, pattern):
        self.clear_steps()
        self.pattern = pattern
        self._update_leds(pattern)

    def _update_leds(self, value):
        """value: 16 bit pattern byte"""
        # split 16-bit pattern into two 8-bit bytes (one for each shift register)
        self.sr.gpio = bytearray((value >> 8 & 0xFF, value & 0xFF))


class NeoPixel:
    STEP_ON_COLOR = (255, 0, 0)
    BAR_COLOR = (255, 0, 255)
    HEAD_COLOR = (255, 255, 0)

    def __init__(self, step_count=16):
        self.pixels = neopixel.NeoPixel(board.GP2, n=step_count, brightness=0.04)
        self.pixels.fill(0)
        self.step_count = step_count
        self.pattern = 0b0
        self._prev_pixel = self.BAR_COLOR

    def next_step(self, step):
        self.pixels[(step - 1) % self.step_count] = self._prev_pixel
        self._prev_pixel = self.pixels[step]
        self.pixels[step] = self.BAR_COLOR if step == 0 else self.HEAD_COLOR

    def update_pattern(self, pattern):
        """pattern: integer representing the pattern"""
        self.pattern = pattern
        for step in range(pattern.bit_length()):
            self.pixels[step] = self.STEP_ON_COLOR if (self.pattern & 2 ** step) > 0 else 0
        self._prev_pixel = self.pixels[0]
