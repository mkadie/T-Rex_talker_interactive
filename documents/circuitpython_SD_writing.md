# Writing files to a CircuitPython SD card from the host (Fruit Jam / RP2350)

How to copy large content (audio packs, images, data) **directly from a PC**
onto the microSD card in an Adafruit Fruit Jam running CircuitPython — and how
to hand write-access back to the device afterward.

Verified 2026-07-12 on a Fruit Jam (RP2350B, CircuitPython 10.1.4).

## The core rule: one writer at a time

A CircuitPython filesystem (the internal `CIRCUITPY` flash **and** a mounted SD
card) can be writable by **either** the USB host **or** the microcontroller —
never both at once. This "single-writer" rule prevents filesystem corruption.

Defaults on the Fruit Jam:

| Filesystem | Mount | MCU access | Host (USB) access |
|---|---|---|---|
| Internal flash | `/` (CIRCUITPY) | read-only | **read-write** |
| SD card | `/sd` (auto-mounted) | **read-write** | read-only |

So out of the box you can copy files onto `CIRCUITPY` but **not** onto the SD —
the SD is the microcontroller's to write, and the host sees it read-only.

### How the SD appears to the host

CircuitPython auto-mounts the SD (the board has default SD pins) and exposes it
as a **second USB Mass Storage LUN** on the same USB device as `CIRCUITPY`.
On Linux both show up under the same `usb-Adafruit_Fruit_Jam_<UID>` by-id entry:

```
usb-Adafruit_Fruit_Jam_<UID>-0:0  -> /dev/sdb   (CIRCUITPY flash, ro=0)
usb-Adafruit_Fruit_Jam_<UID>-0:2  -> /dev/sdd   (SD card,        ro=1)
```

`cat /sys/block/sdd/ro` returns `1`, and any write/remount fails with
`is write-protected`. This is **not** a hardware lock (microSD has no
write-protect tab) and **not** clearable with `blockdev --setrw`, `mount -o
remount,rw`, or a reboot alone — it is the single-writer rule in action.

## Flipping the SD to host-writable

`storage.remount(mount, readonly=<for the MCU>)` sets the microcontroller's
access; the host gets the opposite. To let the **host** write the SD, make the
**MCU** read-only:

```python
# boot.py
import storage
storage.remount("/sd", readonly=True)   # MCU read-only  => USB host read-WRITE
```

Key facts:

- **Must be done in `boot.py`.** Remounting is only reliably allowed at boot.
  (After boot it's permitted only when the host has no write access *and*
  CircuitPython isn't writing — fragile; don't rely on it.)
- **`boot.py` runs only at power-on / hard reset** — not on a soft reboot
  (Ctrl-D, auto-reload on save). After editing `boot.py` you must hard reset.
- From the REPL, `import microcontroller; microcontroller.reset()` performs a
  hard reset (re-runs `boot.py`). The USB serial/drives drop and re-enumerate
  within a few seconds.

## End-to-end provisioning recipe

1. **Add the remount to `boot.py`** (edit it on the `CIRCUITPY` drive — flash
   is host-writable, so this is a normal file copy):

   ```python
   import storage
   try:
       storage.remount("/sd", readonly=True)
       print("boot: /sd handed to host (read-write)")
   except Exception as e:
       print("boot: /sd remount failed:", e)
   ```

2. **Hard reset** so `boot.py` runs:
   `import microcontroller; microcontroller.reset()` (or press RESET).

3. **Confirm host write-access.** After re-enumeration:
   ```bash
   cat /sys/block/sdd/ro          # -> 0
   udisksctl mount -b /dev/sdd1   # mount if not auto-mounted
   touch /media/.../sd/.wtest && rm /media/.../sd/.wtest   # succeeds
   ```

4. **Copy your content**, then `sync`:
   ```bash
   cp -r ./game_i18n/* /media/<user>/<SDLABEL>/sounds/game/
   sync
   ```

5. **Hand the SD back to the device.** Unmount the host's view first (flush),
   then revert `boot.py` and hard reset:
   ```bash
   udisksctl unmount -b /dev/sdd1
   ```
   Remove the `storage.remount("/sd", readonly=True)` block from `boot.py`, then
   `microcontroller.reset()`. Now the MCU can write `/sd` again (needed for
   things like score files) and the host sees it read-only once more.

## Gotchas

- **Device writes stop while host owns the SD.** With `readonly=True` for the
  MCU, code that writes to `/sd` (e.g. `/sd/hiscores.txt`) fails until reverted.
  Keep provisioning a temporary window, or gate the remount behind a
  boot-time button hold so normal boots keep MCU write-access.
- **Always `sync` + unmount the host side before reverting**, or the MCU may see
  a stale/half-written filesystem.
- **`CIRCUITPY` flash stays host-writable throughout**, so you can edit
  `boot.py` even while the SD is handed to the host. Flash and SD access are
  independent.
- Referencing SD files from code: the SD is at `/sd/...`. You can open those
  paths directly (`open("/sd/sounds/game/es/words/apple.wav")`), independent of
  any app-level storage manager.

## One-liner mental model

`storage.remount(path, readonly=BOOL)` — `readonly` is **the microcontroller's**
access. `True` ⇒ host can write. `False` (default) ⇒ device can write. Set it in
`boot.py`, hard reset, and only one side writes at a time.

## Sources

- SD Card | Adafruit Fruit Jam | Adafruit Learning System —
  https://learn.adafruit.com/adafruit-fruit-jam/sd-card
- storage — Storage management, CircuitPython docs —
  https://docs.circuitpython.org/en/latest/shared-bindings/storage/
- Workflows, CircuitPython docs —
  https://docs.circuitpython.org/en/latest/docs/workflows.html
