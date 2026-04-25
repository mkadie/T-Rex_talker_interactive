#!/usr/bin/env python3
"""Generate 6x4 inch reference cards for the Communication Game menus."""

from PIL import Image, ImageDraw, ImageFont
import os

DPI = 300
WIDTH = 6 * DPI   # 1800px
HEIGHT = 4 * DPI   # 1200px

DEV = "/media/trex/CIRCUITPY1"
OUT = os.path.expanduser("~/trex/T-Rex_talker_interactive/out")

# Menu layouts: (image_path, [(label, col, row), ...], cols, rows, title)
MENUS = [
    {
        "title": "Home Screen",
        "image": DEV + "/needs_small.bmp",
        "cols": 4,
        "rows": 2,
        "items": [
            ("THIRSTY", 0, 0),
            ("HUNGRY", 1, 0),
            ("MORE", 2, 0),
            ("BATHROOM", 3, 0),
            ("STINKY", 0, 1),
            ("YES", 1, 1),
            ("NO", 2, 1),
            ("PLEASE", 3, 1),
        ],
    },
    {
        "title": "Food & Drink Screen",
        "image": DEV + "/menus/images/food/food_board.bmp",
        "cols": 4,
        "rows": 2,
        "items": [
            ("WATER", 0, 0),
            ("JUICE", 1, 0),
            ("APPLE", 2, 0),
            ("MILK", 3, 0),
            ("BANANA", 0, 1),
            ("CRACKER", 1, 1),
            ("YOGURT", 2, 1),
            ("BACK", 3, 1),
        ],
    },
]


def make_card(menu, output_path):
    # Create white canvas
    card = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
    draw = ImageDraw.Draw(card)

    # Title area height
    title_h = 140

    # Load and scale the menu image to fill the card below the title
    img = Image.open(menu["image"]).convert("RGB")
    img_area_w = WIDTH - 60  # 30px margin each side
    img_area_h = HEIGHT - title_h - 40  # margin below
    # Scale preserving aspect ratio
    scale = min(img_area_w / img.width, img_area_h / img.height)
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img_scaled = img.resize((new_w, new_h), Image.NEAREST)

    # Center the image
    img_x = (WIDTH - new_w) // 2
    img_y = title_h + 10
    card.paste(img_scaled, (img_x, img_y))

    # Draw title
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
    except OSError:
        title_font = ImageFont.load_default()
        label_font = ImageFont.load_default()

    # Title centered
    bbox = draw.textbbox((0, 0), menu["title"], font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((WIDTH - tw) // 2, 30), menu["title"], fill=(0, 0, 0), font=title_font)

    # Overlay labels on each cell
    cell_w = new_w / menu["cols"]
    cell_h = new_h / menu["rows"]

    for label, col, row in menu["items"]:
        cx = img_x + int(col * cell_w + cell_w / 2)
        cy = img_y + int(row * cell_h + cell_h - 30)

        # Text with background for readability
        bbox = draw.textbbox((0, 0), label, font=label_font)
        lw = bbox[2] - bbox[0]
        lh = bbox[3] - bbox[1]
        tx = cx - lw // 2
        ty = cy - lh // 2

        # Semi-transparent background
        pad = 8
        draw.rectangle(
            [tx - pad, ty - pad, tx + lw + pad, ty + lh + pad],
            fill=(0, 0, 0),
        )
        draw.text((tx, ty), label, fill=(255, 255, 255), font=label_font)

    card.save(output_path, dpi=(DPI, DPI))
    print("Saved:", output_path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for menu in MENUS:
        slug = menu["title"].lower().replace(" ", "_").replace("&", "and")
        path = os.path.join(OUT, f"reference_card_{slug}.png")
        make_card(menu, path)
    print("Done")
