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
- Event-based system to hook into seq/UI events, see _src/main.py_
- Save up to 16 sequences

## Usage
- **Rotate encoder (no buttons held)** → Adjust **TEMPO**

- **Press a button** → Select **voice**

- **Hold a button + rotate encoder**:
  - **Btn 1** → Add/remove **HITS**
  - **Btn 2** → Add/remove **OFFSET**
  - **Btn 3** → Add/remove **STEPS**
  - **Btn 4** → Select sequence **(1–16)**
    - Also press **encoder button** while holding Btn 4 → **Save** sequence

- **Press encoder button** → **PLAY/STOP** sequence

- **Button combos**:
  - **Btn 1 + Btn 2** → **Clear** pattern
  - **Btn 2 + Btn 3** → **Random** pattern

## TODO
- [ ] Porting to Arduino C. Despite CircuitPython is great to play around, it doesn't provide hardware timer interrupts, which is critical to keep tempo consistent. Maybe worth trying plain MicroPython, but C surely is a better idea.
- [ ] Add more voices
- [ ] Sync out
- [x] MIDI sync in
- [x] Improve RC filter on audio PWM pin (currently, just a 4.7k + 1uF cap)
