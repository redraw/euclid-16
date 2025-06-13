import board
import storage
import digitalio

switch = digitalio.DigitalInOut(board.GP21)  # btn 1
switch.switch_to_input(pull=digitalio.Pull.UP)  # default HIGH / True
btn_pressed = not switch.value
print(f"GP21: {btn_pressed=}")

if btn_pressed:
    # filesystem is available for board or host, not both
    # readonly from CircuitPython perspective, write enabled for host.
    storage.remount("/", readonly=True)
