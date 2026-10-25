# AnimePipBoy benchmark: baseline before the speed work

**Board:** `62AB3604F4D0B8E6` (FRUITJAM_CLONE_18), stock CircuitPython 10.1.4.

**Code:** AnimePipBoy as committed (7f5fe5e). The display runs at 24 MHz with
`auto_refresh` on. Board images are 24-bit BMPs on internal flash; the SD
card is not used.

**Taken:** 2026-10-25 with `tools/bench_pipboy.py` (REPL, no files changed).

All times are in milliseconds. Each row is the minimum / average / maximum
over the number of runs shown.

## Screen

| What | n | min | avg | max |
|---|---|---|---|---|
| Read a 61 KB board BMP from flash (raw file read) | 6 | 32.6 | 44.8 | 94.2 |
| `set_background()` Python cost (open + TileGrid) | 12 | 56.9 | 58.2 | 59.2 |
| **Full-screen paint, base board** | 6 | 927.5 | 927.6 | 927.9 |
| **Full-screen paint, food board** | 6 | 935.5 | 935.8 | 936.0 |
| Paint after `restore_background()` (group swap only) | 6 | 934.8 | 935.5 | 937.3 |
| Encoder highlight move: paint | 12 | 52.6 | 100.9 | 105.7 |
| Hint text: `set_text()` Python cost (first call builds the label) | 6 | 11.1 | 27.4 | 107.0 |
| Hint text: paint | 6 | 15.8 | 21.6 | 23.3 |

## Menus and navigation

| What | n | min | avg | max |
|---|---|---|---|---|
| Parse `base_fruitjam.menu` | 6 | 104.3 | 104.8 | 105.1 |
| Parse `food_fruitjam.menu` | 6 | 99.2 | 99.5 | 99.9 |
| Food/Drink **in**, one explicit paint | 3 | 1262.8 | 1263.0 | 1263.3 |
| Back **out**, one explicit paint | 3 | 1255.2 | 1256.8 | 1257.9 |
| **Food/Drink in, as shipped** (`auto_refresh` on) | 3 | 2228.0 | 2304.4 | 2342.9 |
| **Back out, as shipped** (`auto_refresh` on) | 3 | 2227.9 | 2228.5 | 2229.5 |

## Sound and presses

| What | n | min | avg | max | Clip length | Overhead |
|---|---|---|---|---|---|---|
| Play `yes.mp3` | 3 | 1176.3 | 1178.3 | 1181.2 | 966.5 | ~210 |
| Play `ja/yes.mp3` | 3 | 966.2 | 966.7 | 967.0 | 757.6 | ~210 |
| Play `how_much_for_that.mp3` | 3 | 1547.7 | 1569.4 | 1612.6 | 1332.2 | ~240 |
| **Press Yes, whole press as shipped** | 3 | 2258.8 | 2261.9 | 2266.1 | | |
| **Press Swap Language, whole press** | 2 | 4405.6 | 4539.3 | 4673.0 | | |

## Other

| What | Value |
|---|---|
| Boot: `Machine()` init, not counting CircuitPython startup | 7159 ms |
| Free RAM after init (PSRAM) | ~7.9 MB |

## What the numbers say

- **A full-screen paint takes 0.93 s, and almost all of it is
  OnDiskBitmap decoding.** The panel is only 160×128×2 = 40 KB. At 24 MHz that
  is about 14 ms of bus time, and the raw 61 KB file read takes 33–94 ms. The
  other ~800 ms is displayio converting 24-bit pixels from flash one at a
  time. So raising the SPI clock (field-notes idea 1) can only save a few
  ms per paint. The fixes that remove decoding are the ones that matter:
  indexed BMPs, or caching each board as a `displayio.Bitmap` in RAM.
  There is ~7.9 MB free, so caching the two 40 KB boards is easily
  affordable.
- **Navigation, as shipped, paints the screen twice: about 2.2–2.3 s in
  or out**, against 1.26 s with one paint. That confirms the field note.
  The single-paint diff should save about 1 s per navigation, and RAM
  caching would take most of the remaining 1.26 s away.
- **Every word button also costs a full repaint after its sound**
  (`restore_background()`, about 0.93 s). That is why pressing Yes takes
  2.26 s for a 0.97 s clip. The field notes don't mention this, but it is
  the most common press.
- **Swap Language takes about 4.5 s**: the ~1.1 s announcement plus several
  full paints and a menu parse.
- **Sound start-up overhead is a steady ~210–240 ms per clip.**
- **Menu parsing costs ~0.1 s per menu file**, on every navigation.

---

# After: board images cached in RAM, and repaints skipped when nothing changed

`display_manager.py` (now in this folder) has two changes:

- **RAM cache.** The first time a board background is used, its 24-bit BMP is
  converted to an RGB565 `displayio.Bitmap` in RAM (~0.5 s, one time only,
  ~41 KB per board). After that it never decodes from flash again. Other BMP
  formats, or running out of memory, fall back to `OnDiskBitmap`.
- **`restore_background()` does nothing when the screen already shows exactly
  the menu layers.** That removes the extra full repaint before every
  navigation and after every word press.

Measured 2026-10-25 with the same script and board. The user checked it on
the device: colours and highlight are correct, and it feels faster.

| What | Before | After | Speed-up |
|---|---|---|---|
| **Full-screen paint** (board) | 928–936 | **139–140** | 6.7× |
| Paint after `restore_background()` | 935 | **0.5** (skipped) | skipped |
| Encoder highlight move: paint | 101 avg | **27 avg** | 3.7× |
| **Food/Drink in, as shipped** | 2304 avg | **357 avg** | 6.5× |
| **Back out, as shipped** | 2229 avg | **349 avg** | 6.4× |
| **Press Yes, whole press** | 2262 avg | **1237 avg** (= clip + ~0.2 s start-up) | 1.8× |
| **Press Swap Language, whole press** | 4539 avg | **1887 avg** | 2.4× |
| Food board, first use only (one-time convert) | n/a | 553 | one-time |
| Boot: `Machine()` init (base board converted at boot) | 7159 | 7601 | +0.44 s |
| Free RAM at end | ~7.95 MB | ~7.86 MB | −86 KB |

Unchanged on purpose: menu parsing (~0.1 s per file per navigation), sound
start-up (~0.2 s per clip), hint-text paint (~22 ms), and the SPI clock.
Those are the remaining costs to look at next.

---

# Wake from sleep

Software idle on this board drops the screen's power rail (D10). Waking
therefore rebuilds the display driver and repaints, and the main loop then
decides when presses count again. Measured with `tools/bench_pipboy_wake.py`:
it runs the real `_enter_software_idle()` 4 times per stage, with real rail
cuts, woken by a simulated encoder turn at a random moment. Times are from
that wake trigger.

| Stage | Wake → picture | Wake → presses work |
|---|---|---|
| Before (code from earlier today: RAM cache, but stock wake path) | 1269 avg (1211–1298) | 2270 avg (2212–2298) |
| **1: A + B + C** | **617 avg** (611–628) | 1618 avg |
| **2: + D** | 619 avg | **1314 avg** (1308–1321) |
| **3: + E** | 620 avg | **675 avg** (668–680) |

Before the RAM cache, the paint inside the rebuild took 0.93 s instead of
0.07–0.14 s, so "picture" was about 2.0 s that morning.

**What each change is**

- **A: faster ST7735R start-up** (`display_manager.py`, enabled with
  `st7735_fast_init = true` in `config.txt`). The same command sequence as
  `adafruit_st7735r`, but with datasheet-style waits: SWRESET 150→120 ms,
  SLPOUT 500→120 ms, DISPON 100→20 ms. Driver init goes from 921–952 ms to
  431 ms. Boot uses it too.
- **B:** dropped the 0.1 s pause in `rebuild()`, because the sleep manager
  has already waited `full_power_settle_ms` for the rail.
- **C:** the wake poll runs every 20 ms instead of 100 ms (`sleep_manager.py`).
- **D: release gate instead of a fixed 1 s grace** (`machine.py`
  `_after_wake` / `_wake_gate_open`). Presses are ignored until every button
  has read released for 50 ms. With a real button wake this ends when you
  let go.
- **E: no post-wake audio reprogramming while the amp is held in reset.**
  `play()` → `amp_wake()` already reprograms the codec before the first
  sound. So the first sound after a wake starts ~0.6 s later, and input is
  free ~0.64 s sooner.

**Checked on the device:** the user watched the boot and 4 + 4 + 6 wakes
with real rail cuts. All had correct colours and position, none blank.
Real button wakes, twice with sleep on USB: the wake press did **not**
select an item, and the next press played "Yes" cleanly from the speaker
after reprogramming the codec.

Side finding, for next time: the amp is put back into reset after
`periph_idle_timeout` of quiet. **Any** press after a quiet spell, not only
after a wake, pays the same ~0.6–0.7 s codec reprogram before its sound.

---

# Amp idle: first word after a pause

After `periph_idle_timeout` (15 s) of quiet, the amp used to be held in
reset to stop it hissing. Reset wipes the TLV320 codec, so the next sound
first reprogrammed it. Measured on the device, a reset wake took
**643 ms**, almost all of it re-arming jack detection:

| Piece | ms |
|---|---|
| Release from reset | 50 |
| `configure_clocks` | 28 |
| **Jack detection re-arm + 5 matching reads** | **526** |
| `set_audio_route` (route + our levels) | 36 |

**Change** (`audio_player.py`, enabled with `amp_soft_idle = true` in
`config.txt`): "soft idle" switches the active output driver off
(`speaker_output` / `headphone_output = False`) and keeps the codec out of
reset. It still has its clocks, its levels and live jack detection. The
next sound turns the route back on with `set_audio_route()`, about 36 ms.
At your request, outputs now switch off **as soon as each sound finishes**,
not after 15 s, so the board is silent between words. The 15 s
`poll_amp_idle()` check stays as a fallback. A jack change during soft idle
re-routes and stays quiet. Sleep still uses the full reset (lowest power),
and the wake path from the previous section handles that.

| What | Before | After |
|---|---|---|
| Play "Yes" after a quiet spell | 1817 avg | **1239 avg** |
| Play "Yes" back to back | 1176 avg (amp left on) | 1229 avg (on/off each word) |
| Press Yes after a pause, whole press | ~1.82 s + | **1335 avg** |
| Hiss between words | for 15 s after each sound | **none** (outputs off right away) |

Checked on the device by the user: no hiss between words, no pops or clicks
on quick or slow presses, and words play cleanly after a pause.

**Headphones:** powering the headphone drivers down and up again gave a
slight pop before each word. Soft idle now leaves the headphone drivers
powered and only **mutes** them (`headphone_left/right_mute`); waking just
unmutes them. The user confirmed there is no pop now. Plugging in and
unplugging during soft idle re-routes correctly (seen in the log) and stays
quiet.

What's left of the per-sound cost is `play()`'s fixed 0.1 s "dead time"
before playback, the 0.05 s drain after it, and opening the MP3 decoder.
