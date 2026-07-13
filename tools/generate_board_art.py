#!/usr/bin/env python3
"""Generate 320x240 AAC board-background images from .menu files.

The Fruit Jam DVI display renders a menu as a single full-screen board
image (display_manager._load_background -> OnDiskBitmap) with a yellow
cell-sized highlight overlaid on the selected cell. It does NOT composite
per-cell icons at runtime, so each menu needs a pre-rendered board image
whose grid matches the menu's columns x rows.

This tool reads a .menu file, maps each item to a colour emoji icon
(Noto Color Emoji), and composites a themed board: one rounded tile per
cell with the icon, its label, and a corner number badge. Cell geometry
is width//cols x height//rows so it lines up exactly with the runtime
highlight rectangle.

Output is a 24-bit uncompressed BMP (displayio OnDiskBitmap compatible),
matching the existing help.bmp format.

Usage:
    python3 tools/generate_board_art.py                 # build the default set
    python3 tools/generate_board_art.py menus/base.menu out/needs_small.bmp

Part of T-Rex's Rubber Chicken Challenge (TRuCC).
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

# --- geometry ------------------------------------------------------------
W, H = 320, 240

# --- fonts ---------------------------------------------------------------
EMOJI_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMOJI_STRIKE = 109  # Noto Color Emoji ships a single 109px bitmap strike
LABEL_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]

# --- theme (Rubber Chicken Challenge) ------------------------------------
BG_TOP = (18, 32, 58)        # deep navy
BG_BOTTOM = (10, 18, 34)     # darker navy (vertical gradient)
TILE_FILL = (30, 48, 80)     # cell tile
TILE_EDGE = (70, 96, 140)    # cell border
LABEL_COLOR = (255, 255, 255)
BADGE_FILL = (250, 204, 21)  # chicken yellow
BADGE_TEXT = (18, 32, 58)

# --- item id / label -> emoji -------------------------------------------
# Keyed by menu-section id first, then falls back to a lowercased label.
EMOJI_BY_ID = {
    # base.menu
    "tired": "\U0001F634",      # sleeping face
    "happy": "\U0001F60A",      # smiling face with smiling eyes
    "thirsty": "\U0001F964",    # cup with straw (legacy)
    "hungry": "\U0001F37D",     # fork and knife with plate (legacy)
    "more": "\U00002795",       # heavy plus
    "bathroom": "\U0001F6BD",   # toilet
    "stinky": "\U0001F4A9",     # pile of poo
    "yes": "\U00002705",        # check mark button
    "no": "\U0000274C",         # cross mark
    "please": "\U0001F64F",     # folded hands
    "thankyou": "\U0001F64F",
    # food.menu
    "water": "\U0001F4A7",      # droplet
    "juice": "\U0001F9C3",      # beverage box
    "apple": "\U0001F34E",      # red apple
    "milk": "\U0001F95B",       # glass of milk
    "banana": "\U0001F34C",     # banana
    "cracker": "\U0001F36A",    # cookie (closest to cracker)
    "yogurt": "\U0001F963",     # bowl with spoon
    "back_button": "\U00002B05", # left arrow
    "back": "\U00002B05",
}
EMOJI_BY_LABEL = {
    "back": "\U00002B05",
}
FALLBACK_EMOJI = "\U00002753"   # question mark


# --- .menu parsing -------------------------------------------------------
def parse_menu(path):
    """Return (header_dict, [item_dicts]) from a .menu file.

    Each item dict carries its section id under key '_id'.
    """
    header = {}
    items = []
    cur = None
    cur_id = None
    with open(path) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                sect = line[1:-1].strip()
                if sect == "menu":
                    cur = header
                    cur_id = None
                else:
                    cur = {}
                    cur_id = sect
                    cur["_id"] = sect
                    items.append(cur)
                continue
            if "=" in line and cur is not None:
                k, v = line.split("=", 1)
                cur[k.strip()] = v.strip()
    return header, items


def emoji_for(item):
    """Pick an emoji for a menu item by id, then label, then fallback."""
    iid = item.get("_id", "")
    if iid in EMOJI_BY_ID:
        return EMOJI_BY_ID[iid]
    label = item.get("label", "").strip().lower()
    if label in EMOJI_BY_LABEL:
        return EMOJI_BY_LABEL[label]
    return FALLBACK_EMOJI


# --- rendering -----------------------------------------------------------
def _load_label_font(size):
    for cand in LABEL_FONT_CANDIDATES:
        if os.path.exists(cand):
            return ImageFont.truetype(cand, size)
    return ImageFont.load_default()


def _render_emoji(glyph, size):
    """Rasterise one colour emoji to an RGBA image `size` px tall."""
    font = ImageFont.truetype(EMOJI_FONT_PATH, EMOJI_STRIKE,
                              layout_engine=ImageFont.Layout.RAQM)
    canvas = Image.new("RGBA", (EMOJI_STRIKE + 20, EMOJI_STRIKE + 20),
                       (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.text((10, 4), glyph, font=font, embedded_color=True)
    # Crop to the glyph's non-transparent bounds, then scale to `size`.
    bbox = canvas.getbbox()
    if bbox:
        canvas = canvas.crop(bbox)
    return canvas.resize((size, size), Image.LANCZOS)


def _gradient_bg():
    bg = Image.new("RGB", (W, H))
    px = bg.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return bg


def render_board(menu_path):
    header, items = parse_menu(menu_path)
    cols = int(header.get("columns", 4))
    rows = int(header.get("rows", 2))
    zone_w = W // cols
    zone_h = H // rows

    img = _gradient_bg()
    draw = ImageDraw.Draw(img)

    icon_px = min(zone_w, zone_h) - 46
    icon_px = max(28, min(icon_px, 76))
    label_font = _load_label_font(14 if zone_w >= 78 else 12)
    badge_font = _load_label_font(13)

    for item in items:
        pos = int(item.get("position", 0))
        if pos < 1:
            continue
        col = (pos - 1) % cols
        row = (pos - 1) // cols
        x0 = col * zone_w
        y0 = row * zone_h
        x1 = x0 + zone_w - 1
        y1 = y0 + zone_h - 1

        # Rounded tile with a small inset margin.
        m = 4
        draw.rounded_rectangle([x0 + m, y0 + m, x1 - m, y1 - m],
                               radius=10, fill=TILE_FILL, outline=TILE_EDGE,
                               width=2)

        # Icon, centred horizontally, upper portion of the cell.
        icon = _render_emoji(emoji_for(item), icon_px)
        ix = x0 + (zone_w - icon_px) // 2
        iy = y0 + m + 8
        img.paste(icon, (ix, iy), icon)

        # Label, centred under the icon.
        label = item.get("label", item.get("_id", ""))
        lb = draw.textbbox((0, 0), label, font=label_font)
        lw = lb[2] - lb[0]
        lx = x0 + (zone_w - lw) // 2
        ly = iy + icon_px + 3
        draw.text((lx, ly), label, font=label_font, fill=LABEL_COLOR)

        # Number badge, top-left corner.
        bx, by = x0 + m + 4, y0 + m + 4
        draw.ellipse([bx, by, bx + 20, by + 20], fill=BADGE_FILL)
        num = str(pos)
        nb = draw.textbbox((0, 0), num, font=badge_font)
        nw, nh = nb[2] - nb[0], nb[3] - nb[1]
        draw.text((bx + (21 - nw) // 2 - nb[0], by + (21 - nh) // 2 - nb[1]),
                  num, font=badge_font, fill=BADGE_TEXT)

    return img


def save_bmp(img, out_path):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    # 24-bit uncompressed BMP -> displayio OnDiskBitmap compatible.
    img.convert("RGB").save(out_path, format="BMP")
    print("wrote", out_path, img.size)


# --- default build set ---------------------------------------------------
# (menu file, output bmp) — output names match the paths the .menu files
# reference (see each menu's `background =` line and how _load_menu resolves
# it: leading '/' is absolute, otherwise it is under /menus).
DEFAULT_SET = [
    ("menus/base.menu", "out/board_art/needs_small.bmp"),
    ("menus/food.menu", "out/board_art/menus/images/food/food_board.bmp"),
    ("menus/base_fruitjam.menu",
     "out/board_art/menus/images/base/base_board.bmp"),
]


def main(argv):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if len(argv) == 2:
        img = render_board(argv[0])
        save_bmp(img, argv[1])
        return
    for menu_rel, out_rel in DEFAULT_SET:
        menu_path = os.path.join(repo, menu_rel)
        if not os.path.exists(menu_path):
            # menus live on the device; allow an override dir via env.
            alt = os.environ.get("MENUS_DIR")
            if alt:
                menu_path = os.path.join(alt, os.path.basename(menu_rel))
        if not os.path.exists(menu_path):
            print("skip (menu not found):", menu_path)
            continue
        img = render_board(menu_path)
        save_bmp(img, os.path.join(repo, out_rel))


if __name__ == "__main__":
    main(sys.argv[1:])
