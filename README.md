# euclid-16

This is a prototype of a sequencer made in a Raspberry Pi Pico. Particulary, an euclidean sequencer, whose steps can be added/removed uniformely in the grid by rotating the encoder.


https://user-images.githubusercontent.com/10843208/217061688-98ad8c04-bbb4-4034-a97a-8226e16e5d99.mp4


For the moment, features are:
- 4 voices
- 16 steps
- Audio output through PWM (optionally I2S)
- MIDI USB note output
- Clock input 5V trigger pulse (ie. used by Korg Volca, etc)
- 16 led using 2 shift registers 74hc595, or NeoPixel display
- Event-based system to hook into seq/UI events, see _code.py_
- Save up to 16 sequences

## Usage
If encoder is rotated without holding any button, it changes TEMPO.

Button presses select voices, however if a button a holded and encoder is rotated, they have different actions.
- btn #1: add/remove HITS
- btn #2: add/remove OFFSET
- btn #3: add/remove STEPS
- btn #4: schedule sequence 1-16
  - if encoder button is pressed when btn is held, sequence is saved.

A single encoder press, PLAY/STOP sequence.
- btn #1 + #2: clear pattern
- btn #2 + #3: random pattern

## TODO
- Porting to Arduino C. Despite CircuitPython is great to play around, it doesn't provide hardware timer interrupts, which is critical to keep tempo consistent. Maybe worth trying plain MicroPython, but C surely is a better idea.
- Add more voices
- Sync out
- MIDI sync in
- Improve RC filter on audio PWM pin (currently, just a 4.7k + 1uF cap)

![](https://www.ontrak.net/Pwm1.gif)
