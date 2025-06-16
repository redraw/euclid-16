import board
import storage
import digitalio

switch = digitalio.DigitalInOut(board.GP21)  # btn 1
switch.switch_to_input(pull=digitalio.Pull.UP)  # default HIGH / True
readonly = not switch.value

# filesystem is available for board or host, not both
# readonly from CircuitPython perspective, write enabled for host.
print(f"CircuitPython {readonly=}.")
storage.remount("/", readonly=readonly)
