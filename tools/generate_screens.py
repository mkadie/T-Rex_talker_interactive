#!/usr/bin/env python3
"""Pre-render every game screen in every language as a full 320x240 BMP.

The device is a screen-swapper: instead of drawing translated text at
runtime (CircuitPython's built-in font is ASCII-only and can't render
Thai / Arabic / CJK / Devanagari / Bengali / Cyrillic), we bake each
screen into an image here with Pillow + Noto fonts, so every script
renders perfectly. The game just puts up the right file.

Output (mirrors the SD layout /sd/screens/<code>/):
    out/screens/<code>/title.bmp        title + start / language hints
    out/screens/<code>/board_base.bmp   base play grid (page 1)
    out/screens/<code>/board_food.bmp   food play grid (page 2)
    out/screens/<code>/finished.bmp     end-of-round screen

Dynamic data (high-score digits, entered name) is still overlaid at
runtime with the ASCII font — those are numbers / A-Z, which the built-in
font handles.

Translations come from Google Translate (deep-translator), cached in
out/game_i18n/translations.json (shared with the audio build so labels
match the spoken words). Requires Pillow with raqm for shaping.

Usage:
    python tools/generate_screens.py [--only es,ja] [--force]
"""

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import generate_board_art as art          # emoji render, theme, geometry
from generate_language_images import SCRIPT_FONTS, LATIN_FONT

W, H = 320, 240
OUT = "out/screens"
CACHE = "out/game_i18n/translations.json"

# code, gtts (unused here), google-translate code, english name, native name
LANGS = [
    ("en", "en",    "en",    "English",    "English"),
    ("th", "th",    "th",    "Thai",       "ไทย"),
    ("ja", "ja",    "ja",    "Japanese",   "日本語"),
    ("zh", "zh-cn", "zh-CN", "Mandarin",   "中文"),
    ("hi", "hi",    "hi",    "Hindi",      "हिन्दी"),
    ("es", "es",    "es",    "Spanish",    "Español"),
    ("fr", "fr",    "fr",    "French",     "Français"),
    ("ar", "ar",    "ar",    "Arabic",     "العربية"),
    ("bn", "bn",    "bn",    "Bengali",    "বাংলা"),
    ("pt", "pt",    "pt",    "Portuguese", "Português"),
    ("ru", "ru",    "ru",    "Russian",    "Русский"),
    ("cs", "cs",    "cs",    "Czech",      "Čeština"),
    ("de", "de",    "de",    "German",     "Deutsch"),
]

# 4x2 board layouts (position, item-id) — must match base.menu / food.menu.
BASE_CELLS = [(1, "tired"), (2, "happy"), (3, "more"), (4, "bathroom"),
              (5, "stinky"), (6, "yes"), (7, "no"), (8, "please")]
FOOD_CELLS = [(1, "water"), (2, "juice"), (3, "apple"), (4, "milk"),
              (5, "banana"), (6, "cracker"), (7, "yogurt"), (8, "back")]

# English source strings to translate (labels reuse the audio cache keys).
LABELS = ["tired", "happy", "more", "bathroom", "stinky", "yes", "no",
          "please", "water", "juice", "apple", "milk", "banana", "cracker",
          "yogurt", "back"]
UI = {
    "start": "Press Button 2 to start",
    "lang": "Button 1: change language",
    "finished": "Great job!",
    "finished2": "You finished the round!",
}

TITLE_BRAND = "T-Rex's Rubber\nChicken Challenge"  # brand name, kept in English


# --- silly cartoon rubber chicken ---------------------------------------
def draw_chicken(size):
    """Return an RGBA image of a goofy plucked rubber chicken."""
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    YEL = (247, 208, 70); YEL2 = (226, 176, 44); RED = (214, 54, 54)
    ORA = (243, 146, 32); BLK = (34, 34, 34)
    # plump body
    d.ellipse([s*0.16, s*0.40, s*0.84, s*0.80], fill=YEL, outline=YEL2, width=2)
    # tail stub
    d.polygon([(s*0.80, s*0.50), (s*0.95, s*0.44), (s*0.82, s*0.64)], fill=YEL)
    # neck
    d.line([(s*0.31, s*0.56), (s*0.30, s*0.27)], fill=YEL, width=int(s*0.11))
    # head
    d.ellipse([s*0.19, s*0.12, s*0.43, s*0.34], fill=YEL, outline=YEL2, width=2)
    # comb (three red bumps)
    for cx in (0.25, 0.31, 0.37):
        d.ellipse([s*(cx-0.035), s*0.05, s*(cx+0.035), s*0.16], fill=RED)
    # open beak, pointing left
    d.polygon([(s*0.19, s*0.20), (s*0.03, s*0.22), (s*0.19, s*0.25)], fill=ORA)
    d.polygon([(s*0.19, s*0.25), (s*0.05, s*0.30), (s*0.19, s*0.29)],
              fill=(214, 120, 18))
    # wattle
    d.ellipse([s*0.16, s*0.28, s*0.24, s*0.39], fill=RED)
    # silly X eye
    ex, ey, r = s*0.31, s*0.22, s*0.032
    d.line([(ex-r, ey-r), (ex+r, ey+r)], fill=BLK, width=2)
    d.line([(ex-r, ey+r), (ex+r, ey-r)], fill=BLK, width=2)
    # wing
    d.arc([s*0.36, s*0.48, s*0.66, s*0.74], 200, 20, fill=YEL2, width=3)
    # dangly legs
    for lx in (0.44, 0.58):
        d.line([(s*lx, s*0.78), (s*lx, s*0.93)], fill=ORA, width=3)
        for dx in (-0.045, 0.0, 0.045):
            d.line([(s*lx, s*0.93), (s*(lx+dx), s*0.98)], fill=ORA, width=2)
    return im


def paste_alpha(base, overlay, xy, opacity=1.0):
    if opacity < 1.0:
        a = overlay.split()[3].point(lambda p: int(p * opacity))
        overlay = overlay.copy()
        overlay.putalpha(a)
    base.paste(overlay, xy, overlay)


def load_cache():
    try:
        with open(CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with open(CACHE, "w") as f:
        json.dump(c, f, ensure_ascii=False, indent=0)


def translate(text, gt_code, cache):
    if gt_code == "en":
        return text
    key = gt_code + "\t" + text
    if key in cache:
        return cache[key]
    from deep_translator import GoogleTranslator
    try:
        out = GoogleTranslator(source="en", target=gt_code).translate(text)
        if out:
            cache[key] = out
            return out
    except Exception as e:
        print("   translate fail:", text, e)
    return text


def font_for(code, size):
    path = SCRIPT_FONTS.get(code, LATIN_FONT)
    return ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)


def fit(draw, text, code, max_w, hi, lo=12):
    for size in range(hi, lo - 1, -2):
        f = font_for(code, size)
        l, _, r, _ = draw.textbbox((0, 0), text, font=f)
        if r - l <= max_w:
            return f
    return font_for(code, lo)


def _center(draw, cx, y, text, font, fill):
    draw.text((cx, y), text, font=font, fill=fill,
              anchor="mm", embedded_color=False)


# --- board screen --------------------------------------------------------
def render_board(cells, code, labels):
    cols, rows = 4, 2
    zw, zh = W // cols, H // rows
    img = art._gradient_bg()
    draw = ImageDraw.Draw(img)
    icon_px = 56
    for pos, iid in cells:
        col, row = (pos - 1) % cols, (pos - 1) // cols
        x0, y0 = col * zw, row * zh
        m = 4
        draw.rounded_rectangle([x0 + m, y0 + m, x0 + zw - 1 - m, y0 + zh - 1 - m],
                               radius=10, fill=art.TILE_FILL,
                               outline=art.TILE_EDGE, width=2)
        icon = art._render_emoji(art.EMOJI_BY_ID.get(iid, art.FALLBACK_EMOJI),
                                 icon_px)
        ix = x0 + (zw - icon_px) // 2
        iy = y0 + m + 6
        img.paste(icon, (ix, iy), icon)
        label = labels.get(iid, iid)
        cx = x0 + zw // 2
        ly = iy + icon_px + 4
        f = fit(draw, label, code, zw - 6, 16, 9)
        lb = draw.textbbox((0, 0), label, font=f)
        if lb[2] - lb[0] <= zw - 6 or " " not in label:
            _center(draw, cx, ly + 6, label, f, art.LABEL_COLOR)
        else:  # wrap long (translated) labels onto two lines
            words = label.split(" ")
            mid = (len(words) + 1) // 2
            l1, l2 = " ".join(words[:mid]), " ".join(words[mid:])
            f2 = fit(draw, max(l1, l2, key=len), code, zw - 6, 13, 8)
            _center(draw, cx, ly, l1, f2, art.LABEL_COLOR)
            _center(draw, cx, ly + 13, l2, f2, art.LABEL_COLOR)
        # number badge
        bx, by = x0 + m + 3, y0 + m + 3
        draw.ellipse([bx, by, bx + 19, by + 19], fill=art.BADGE_FILL)
        nf = font_for("en", 12)
        _center(draw, bx + 10, by + 10, str(pos), nf, art.BADGE_TEXT)
    return img


# --- title screen --------------------------------------------------------
def render_title(code, en_name, ui):
    img = art._gradient_bg()
    # faint rubber-chicken watermark behind the text
    ch = draw_chicken(150)
    paste_alpha(img, ch, ((W - 150) // 2, 58), opacity=0.28)
    draw = ImageDraw.Draw(img)
    # brand (English), yellow, top
    bf = font_for("en", 22)
    y = 14
    for line in TITLE_BRAND.split("\n"):
        _center(draw, W // 2, y, line, bf, art.BADGE_FILL)
        y += 28
    # SELECTED LANGUAGE — English name, prominent, so a non-reader can see
    # exactly which language is active.
    nf = font_for("en", 28)
    _center(draw, W // 2, 88, en_name, nf, (0, 255, 255))
    # translated start hint (Button 2 — there is no coloured button)
    sf = fit(draw, ui["start"], code, W - 20, 20, 12)
    _center(draw, W // 2, 134, ui["start"], sf, (255, 255, 255))
    # translated language hint (Button 1)
    lf = fit(draw, ui["lang"], code, W - 20, 17, 12)
    _center(draw, W // 2, 162, ui["lang"], lf, (170, 200, 255))
    return img


# --- finished screen -----------------------------------------------------
def render_finished(code, ui):
    img = art._gradient_bg()
    # a happy rubber chicken celebrating
    ch = draw_chicken(96)
    paste_alpha(img, ch, ((W - 96) // 2, 118), opacity=0.95)
    draw = ImageDraw.Draw(img)
    f1 = fit(draw, ui["finished"], code, W - 20, 42, 20)
    _center(draw, W // 2, 40, ui["finished"], f1, (34, 220, 120))
    f2 = fit(draw, ui["finished2"], code, W - 20, 24, 13)
    _center(draw, W // 2, 84, ui["finished2"], f2, (255, 255, 255))
    return img


def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 8-bit palette BMP — ~3x smaller than 24-bit, so it loads fast and fits
    # in RAM via adafruit_imageload (display never competes with audio for
    # the SD, and language scrolling stays responsive).
    img.convert("RGB").convert(
        "P", palette=Image.ADAPTIVE, colors=256).save(path, format="BMP")
    print("  wrote", path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    only = set(c.strip() for c in args.only.split(",") if c.strip())
    cache = load_cache()

    for code, _g, gt, en_name, _native in LANGS:
        if only and code not in only:
            continue
        print("===", en_name, "===")
        labels = {w: translate(w, gt, cache) for w in LABELS}
        # the "please" button conveys please + thank you
        labels["please"] = translate("please and thank you", gt, cache)
        ui = {k: translate(v, gt, cache) for k, v in UI.items()}
        save_cache(cache)
        d = "%s/%s" % (OUT, code)
        jobs = {
            "board_base.bmp": lambda: render_board(BASE_CELLS, code, labels),
            "board_food.bmp": lambda: render_board(FOOD_CELLS, code, labels),
            "title.bmp": lambda: render_title(code, en_name, ui),
            "finished.bmp": lambda: render_finished(code, ui),
        }
        for name, fn in jobs.items():
            path = "%s/%s" % (d, name)
            if os.path.exists(path) and not args.force:
                print("  skip", path)
                continue
            save(fn(), path)
    save_cache(cache)
    print("done")


if __name__ == "__main__":
    main()
