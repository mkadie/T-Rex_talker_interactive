"""
Enable USB host on the Fruit Jam's PIO-USB port.

Must run from boot.py — the USB stack only initializes once at startup.
After saving this file the first time, do a HARD reset (unplug/replug
USB power, or press the reset button) for it to take effect.

After this runs:
  - The dedicated host USB-C port can power and enumerate devices
    (keyboards, mice, hubs).
  - usb.core.find() in code.py returns the connected devices.
"""
import board
import digitalio
import usb_host

# Power the host bus so plugged-in devices boot.
_pwr = digitalio.DigitalInOut(board.USB_HOST_5V_POWER)
_pwr.direction = digitalio.Direction.OUTPUT
_pwr.value = True

# Bring the PIO-USB host controller up on the host data lines.
usb_host.Port(board.USB_HOST_DATA_PLUS, board.USB_HOST_DATA_MINUS)
