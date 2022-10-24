import board
import storage
import digitalio

switch = digitalio.DigitalInOut(board.GP21)
switch.switch_to_input(pull=digitalio.Pull.UP)

storage.remount("/", readonly=not switch.value)