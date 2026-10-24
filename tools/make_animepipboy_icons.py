"""Generate the AnimePipBoy base-menu tiles for cells 4 and 5 and patch them into
the full-board background.

  howmuch.bmp   "How much for that?"  — $ on the cream WC-style tile
  swaplang.bmp  "Swap Language"       — speech bubble with "A あ"

Tiles are 53x64 RGB, drawn at 4x and downsampled so edges antialias like
the existing Moana-palette tiles. The board background (160x128) has the
tiles baked in with the grid lines drawn over them, so the new tiles are
pasted at their cell origins and the old grid-line pixels restored.

Usage:
    python3 tools/make_animepipboy_icons.py <menus/images/base dir>
"""

import sys
from PIL import Image, ImageDraw, ImageFont

CREAM = (249, 232, 172)
TEAL = (21, 174, 171)
DARK = (35, 31, 32)
WHITE = (255, 255, 255)
GRID = (50, 99, 104)

W, H = 53, 64
S = 4  # supersample

BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CJK_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
CJK_JP_INDEX = 0  # Noto Sans CJK JP is face 0 in the .ttc


def _canvas():
    im = Image.new("RGB", (W * S, H * S), WHITE)
    return im, ImageDraw.Draw(im)


def _center_text(d, cx, cy, text, font):
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text((cx - (l + r) / 2, cy - (t + b) / 2), text, font=font, fill=DARK)


def _finish(im):
    return im.resize((W, H), Image.LANCZOS)


def howmuch():
    im, d = _canvas()
    # Same rounded tile as the generated WC / Food-Drink cells.
    d.rounded_rectangle((2 * S, 2 * S, 50 * S + S - 1, 61 * S + S - 1),
                        radius=9 * S, fill=CREAM, outline=TEAL, width=2 * S)
    _center_text(d, W * S / 2, 32 * S, "$",
                 ImageFont.truetype(BOLD, 40 * S))
    return _finish(im)


def swaplang():
    im, d = _canvas()
    body = (3 * S, 7 * S, 50 * S, 46 * S)
    # Tail first so the body's outline covers its top join.
    tail = [(11 * S, 42 * S), (9 * S, 58 * S), (24 * S, 44 * S)]
    d.polygon(tail, fill=CREAM, outline=TEAL)
    d.line(tail[:2], fill=TEAL, width=2 * S)
    d.line(tail[1:], fill=TEAL, width=2 * S)
    d.rounded_rectangle(body, radius=11 * S, fill=CREAM,
                        outline=TEAL, width=2 * S)
    # Re-fill the tail/body seam so the outline doesn't cut across it.
    d.polygon([(13 * S, 43 * S), (11 * S, 53 * S), (22 * S, 43 * S)],
              fill=CREAM)
    cy = 26.5 * S
    _center_text(d, 15 * S, cy, "A", ImageFont.truetype(BOLD, 20 * S))
    _center_text(d, 37 * S, cy, "あ",
                 ImageFont.truetype(CJK_BOLD, 20 * S, index=CJK_JP_INDEX))
    return _finish(im)


def patch_board(base_dir, tiles):
    """Paste tiles into base_board.bmp at their cell origins, keeping the
    grid lines that were drawn over the old tiles."""
    board = Image.open(base_dir + "/base_board.bmp").convert("RGB")
    for (x, y), old_name, new_img in tiles:
        old = Image.open(base_dir + "/" + old_name).convert("RGB")
        keep = [(i, j) for j in range(H) for i in range(W)
                if board.getpixel((x + i, y + j)) == GRID
                and old.getpixel((i, j)) != GRID]
        board.paste(new_img, (x, y))
        for i, j in keep:
            board.putpixel((x + i, y + j), GRID)
    board.save(base_dir + "/base_board.bmp")


def main():
    base_dir = sys.argv[1].rstrip("/")
    hm, sl = howmuch(), swaplang()
    patch_board(base_dir, [((0, 64), "bathroom.bmp", hm),
                           ((53, 64), "play.bmp", sl)])
    hm.save(base_dir + "/howmuch.bmp")
    sl.save(base_dir + "/swaplang.bmp")
    print("wrote howmuch.bmp, swaplang.bmp, patched base_board.bmp")


if __name__ == "__main__":
    main()
