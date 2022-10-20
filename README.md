# euclid-pico-seq

This is a prototype of a sequencer made in a Raspberry Pi Pico. Particulary, an euclidean sequencer, whose steps can be added/removed uniformely in the grid by rotating the encoder.

![IMG_20221020_154256070](https://user-images.githubusercontent.com/10843208/197031804-b4de262d-72a9-4bc5-854a-e78b9255dff9.jpg)


For the moment, features are:
- 4 voices
- Audio output through PWM (optionally I2S)
- MIDI USB output
- Clock input 5V trigger pulse (ie. used by Korg Volca, etc)
- NeoPixel, or 16 led using 2 shift registers 74hc595
- Event-based system to hook into seq/UI events, for [example](https://github.com/redraw/euclid-pico-seq/blob/v1.0.0/code.py#L62-L85)

## Usage
Button presses select voices, however if a button a holded and encoder is rotated, they have different actions.
- btn #1: add/remove HITS
- btn #2: add/remove OFFSET
- btn #3: add/remove STEPS

If encoder is rotated without holding any button, it changes TEMPO.

## TODO
- Porting to Arduino C. Despite CircuitPython is great to play around, it doesn't provide hardware timer interrupts, which is critical to keep tempo consistent. Maybe worth trying plain MicroPython, but C surely is a better idea.
- Add more voices
- Sync out
- Improve LC filter on audio PWM pin (currently, just a 4.7k + 1uF cap)

![](https://www.ontrak.net/Pwm1.gif)
