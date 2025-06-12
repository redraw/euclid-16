import board
import storage
import digitalio

switch = digitalio.DigitalInOut(board.GP21)
switch.switch_to_input(pull=digitalio.Pull.UP)
print(f"Btn 1: {switch.value=}")
