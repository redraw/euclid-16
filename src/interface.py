import countio
import rotaryio
import busio
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

LEDS_595_SCLK = board.GP2
LEDS_595_DATA = board.GP3
LEDS_595_LATCH_PIN = board.GP4

SYNC_CLOCK_IN = board.GP13  # assumes PPQN = 4


class UI(event.EventEmitter):
    def __init__(self):
        super().__init__()
        self._now = ticks_ms()
        self._last_hold_millis = ticks_ms()

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

        self.clock_in = countio.Counter(SYNC_CLOCK_IN, edge=countio.Edge.RISE)
        self._last_clock_in_count = 0
        self._clock_pulses = 0

    def update(self):
        self._now = ticks_ms()
        self.update_encoder()
        self.update_buttons()
        self.sync_clock_in()

    def update_encoder(self):
        self.encoder_button.update()
        position = self.encoder.position

        if None not in (position, self._last_encoder_position):
            self._encoder_delta = position - self._last_encoder_position
        self._last_encoder_position = position

    def update_buttons(self):
        for idx, button in enumerate(self.buttons):
            button.update()

            if button.pressing and self._encoder_delta:
                if self.active_menu != idx:
                    self.active_menu = idx

                # Hits
                if idx == 0:
                    self.emit(event.UI_HITS_VALUE_CHANGE, self.active_voice, self._encoder_delta)

                # Offset
                elif idx == 1:
                    self.emit(event.UI_OFFSET_VALUE_CHANGE, self.active_voice, self._encoder_delta)

                # Length
                elif idx == 2:
                    self.emit(event.UI_STEP_LENGTH_VALUE_CHANGE, self.active_voice, self._encoder_delta)
                
                # Load sequence
                elif idx == 3:
                    self.emit(event.UI_SEQUENCE_SCHEDULE, self._encoder_delta)

            elif button.rose and self.active_menu == idx:
                self.active_menu = -1

            # Change voice
            elif button.rose:
                self.active_voice = idx
                self.emit(event.UI_VOICE_CHANGE, self.active_voice)

        # Sequences mode
        if self.buttons[3].fell:
            self.emit(event.UI_SEQUENCE_MODE, True)

        if self.buttons[3].rose:
            self.emit(event.UI_SEQUENCE_MODE, False)

        # Save sequence
        if self.buttons[3].pressing and self.encoder_button.rose:
            self.emit(event.UI_SEQUENCE_SAVE)

        hold_millis = ticks_diff(self._now, self._last_hold_millis)

        # Reset pattern (btn 1 & 2 pressed for 1s)
        if all(self.buttons[i].pressing for i in (0, 1)) and hold_millis > 1000:
            self._last_hold_millis = self._now
            self.emit(event.UI_TRIGGER_RESET_PATTERN)

        # Random pattern (btn 2 & 3 pressed for 500ms)
        if all(self.buttons[i].pressing for i in (2, 3)) and hold_millis > 500:
            self._last_hold_millis = self._now
            self.emit(event.UI_PATTERN_RANDOMIZE)

        # Turn encoder (without buttons pressed)
        if not any(button.pressing for button in self.buttons):
            if self.encoder_button.fell:
                self.emit(event.UI_PLAY_STOP)

            if self._encoder_delta:
                self.emit(event.UI_TEMPO_VALUE_CHANGE, self._encoder_delta)

    def sync_clock_in(self):
        count = self.clock_in.count
        if count == self._last_clock_in_count:
            return

        self._clock_pulses += 1
        self._last_clock_in_count = count

        self.emit(event.UI_SYNC_CLOCK_IN, self._now)


class LED:
    def __init__(self):
        self.tempo_pin = digitalio.DigitalInOut(TEMPO_LED_PIN)
        self.tempo_pin.direction = digitalio.Direction.OUTPUT
        self.tempo_pin.value = False

        spi = busio.SPI(LEDS_595_SCLK, MOSI=LEDS_595_DATA)
        latch_pin = digitalio.DigitalInOut(LEDS_595_LATCH_PIN)
        self.sr = adafruit_74hc595.ShiftRegister74HC595(spi, latch_pin, number_of_shift_registers=2)

        self.pattern = 0b0
        self.sequence_mode = False
        self.saving_mode = False
        self.sequence_idx = 0

    def clear(self):
        self.sr.gpio = bytearray((0, 0))

    def toggle_tempo_led(self, step):
        """turn on tempo led on even numbers"""
        self.tempo_pin.value = step % 4 == 0

    def next_step(self, step):
        """sum up pattern and current step in an OR operation"""
        if self.sequence_mode or self.saving_mode: 
            return
        value = self.pattern | 1 << step
        self._update_leds(value)

    def update_pattern(self, pattern):
        self.pattern = pattern
        if self.sequence_mode or self.saving_mode:
            return
        self.show_pattern()

    def set_sequence_mode(self, enabled):
        self.sequence_mode = enabled
        if enabled:
            self.show_sequence()
        else:
            self.show_pattern()

    def set_saving_mode(self, enabled):
        self.saving_mode = enabled
        if enabled:
            self._update_leds(0xFFFF)
        else:
            self.clear()

    def select_sequence(self, idx):
        self.sequence_idx = idx
        self.show_sequence()

    def show_pattern(self):
        self.clear()
        self._update_leds(self.pattern)

    def show_sequence(self):
        self.clear()
        self._update_leds(1 << self.sequence_idx)
    
    def _update_leds(self, value):
        """value: 16 bit pattern byte"""
        # split 16-bit pattern into two 8-bit bytes (one for each shift register)
        # to display the bits as LSB-first
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
            self.pixels[step] = self.STEP_ON_COLOR if (self.pattern & 1 << step) > 0 else 0
        self._prev_pixel = self.pixels[0]
